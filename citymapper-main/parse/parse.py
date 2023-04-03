import pandas as pd
import psycopg2, datetime, sys, geojson, os
from io import StringIO
from sqlalchemy import create_engine
from schema import sql_schema
from os.path import expanduser

os.chdir(sys.path[0])
sys.path.append('../modules')
import params

# See params.py
data_path, user, password, database, host = params.get_variables()

print("variables:" + str(data_path) + " " + str(user) + " " + str(password) + " " + str(database) + " " + str(host))

sys.path.append(data_path)
dp = expanduser(data_path)
conn = psycopg2.connect(database=str(database), user=str(user), host=str(host), password=str(password))
cursor = conn.cursor()
print("database projet connected to the remote server")
engine = create_engine(
    'postgresql+psycopg2://' + str(user) + ':' + str(password) + '@' + str(host) + '/' + str(database))


# copy dataFrame into a table defined in the schema
def copy_to_db(df, table):
    print(df)
    df.to_sql(table, con=engine, if_exists='append', index=False)

    try:
        cursor.execute(f"""select * from {table}""")
        print(f"successfully copied the dataframe into {table}")
    except (Exception, psycopg2.DatabaseError) as error:
        print("Error: %s" % error)
        conn.rollback()
        cursor.close()
        return 1


def create_nodes():
    nodes = pd.read_csv(dp + 'network_' + 'nodes.csv', delimiter=';')
    nodes.columns = nodes.columns.str.lower()
    nodes['name'] = nodes['name'].str.lower()
    copy_to_db(nodes, 'nodes')


def create_temporal_day():
    temporal_day = pd.read_csv(dp + 'network_temporal_day.csv', delimiter=';')
    temporal_day.columns = temporal_day.columns.str.lower()

    def secs(time_ut):
        """return number of seconds since midnigh, so we can later compare dep_time_ut with our current unix time"""
        relative_time = datetime.datetime.utcfromtimestamp(time_ut).strftime('%Y-%m-%d %H:%M:%S')[-8:].split(':')
        return int(relative_time[0]) * 3600 + int(relative_time[1]) * 60 + int(relative_time[2])

    dep = temporal_day['dep_time_ut']
    dep = dep.apply(secs)
    arr = temporal_day['arr_time_ut']
    arr = arr.apply(secs)
    temporal_day['dep_time_ut'] = dep
    temporal_day['arr_time_ut'] = arr

    copy_to_db(temporal_day, 'temporal_day')



def create_routes():
    with open(dp + 'routes.geojson') as f:
        gj = geojson.load(f)['features']

    data = [[line['properties']['route_type'], line['properties']['route_name'], line['properties']['route_I']] for line
            in gj]
    routes = pd.DataFrame(data, columns=['route_type', 'route_name', 'route_I'])
    routes.columns = routes.columns.str.lower()
    copy_to_db(routes, 'routes')

    cursor.execute("""
       SELECT route_type, route_name, min(route_i) AS route_rps_i
INTO route_rps
FROM routes
GROUP BY route_type, route_name;
ALTER TABLE route_rps
ADD PRIMARY KEY (route_rps_i),
ADD FOREIGN KEY (route_rps_i) REFERENCES routes (route_i),
ADD CONSTRAINT unique_route_name UNIQUE (route_type, route_name);

        """)
    conn.commit()

    cursor.execute("""
    select route_i, route_rps.route_rps_i into routexsuper
    from routes INNER JOIN route_rps
    ON routes.route_type=route_rps.route_type AND routes.route_name = route_rps.route_name
    """)
    conn.commit()

    cursor.execute("""ALTER TABLE routexsuper
        ADD PRIMARY KEY (route_i),
        ADD FOREIGN KEY (route_i) references routes (route_i),
        ADD FOREIGN KEY (route_rps_i) references route_rps (route_rps_i)""")
    conn.commit()


def create_combined():
    comb = pd.read_csv(dp + 'network_combined.csv', delimiter=';')
    comb.columns = comb.columns.str.lower()
    comb_split_routes = comb['route_i_counts'].str.split(',|:')
    comb_split_routes = pd.DataFrame(comb_split_routes)
    comb = pd.concat([comb[['from_stop_i', 'to_stop_i', 'duration_avg']], comb_split_routes], axis=1)
    comb = comb.explode('route_i_counts')
    comb = comb.iloc[::2]
    comb = comb.rename(columns={'route_i_counts': 'route_i'})
    print(comb)
    copy_to_db(comb, 'combined')

    cursor.execute("""select DISTINCT from_stop_i, to_stop_i, duration_avg, routexsuper.route_rps_i into super_route_comb
    from combined
    INNER JOIN routexsuper ON combined.route_i = routexsuper.route_i""")
    conn.commit()

    cursor.execute("""ALTER TABLE super_route_comb
    ADD PRIMARY KEY (from_stop_i, to_stop_i, route_rps_i),
    ADD FOREIGN KEY (route_rps_i) references route_rps(route_rps_i)""")
    conn.commit()


def create_stoproutename():
    cursor.execute("""
            SELECT from_stop_i, to_stop_i, route_i into stopxroute
            FROM
            combined""")
    conn.commit()
    cursor.execute("""
    ALTER TABLE stopxroute
    ADD COLUMN stop_i numeric;
    INSERT INTO stopxroute (stop_i, route_i, from_stop_i, to_stop_i)
    SELECT DISTINCT stop_i, route_i, from_stop_i, to_stop_i
    FROM (
        SELECT from_stop_i AS stop_i, route_i, from_stop_i, to_stop_i
        FROM combined
        UNION ALL
        SELECT to_stop_i AS stop_i, route_i, from_stop_i, to_stop_i
        FROM combined
    ) AS temp_table;
    
    DELETE FROM stopxroute
    WHERE stop_i IS NULL;""")
    conn.commit();
    cursor.execute("""
        ALTER TABLE stopxroute
        ADD PRIMARY KEY (from_stop_i, to_stop_i, route_i, stop_i),
        ADD FOREIGN KEY (from_stop_i, to_stop_i, route_i) references  combined (from_stop_i, to_stop_i, route_i)""")
    conn.commit()
    cursor.execute("""select distinct nodes.name, A.stop_I, route_type, route_name into stoproutename
    from stopxroute as A
    INNER JOIN routes ON A.route_i = routes.route_i
    INNER JOIN nodes ON A.stop_i = nodes.stop_i
    order by A.stop_I""")
    conn.commit()
    cursor.execute("""ALTER TABLE stoproutename
     ADD PRIMARY KEY (stop_i, route_type, route_name),
     ADD FOREIGN KEY (route_type, route_name) references route_rps(route_type, route_name),
     ADD FOREIGN KEY (stop_i) references nodes(stop_i)""")


# walk + combxwalk + short_walk

def create_walk():
    walk = pd.read_csv(dp + 'network_walk.csv', delimiter=';')
    walk.columns = walk.columns.str.lower()
    walk['d_walk'] /= 2.5  ### we assumed a person walks at 2.5 m.s-1
    walk['route_i'] = 'w'
    walk = walk.drop(columns=['d'])
    copy_to_db(walk, 'walk')
    walk = walk.rename(columns={'d_walk': 'duration_avg'})

    comb = pd.read_sql("SELECT * FROM combined;", engine)
    combxwalk = pd.concat([walk, comb])
    copy_to_db(combxwalk, 'combxwalk')




    query = """select * into short_walk from walk WHERE d_walk < 300;
    ALTER TABLE short_walk
    ADD PRIMARY KEY (from_stop_i, to_stop_i),
    ADD FOREIGN KEY (from_stop_i, to_stop_i) references walk (from_stop_i, to_stop_i);
    """
    cursor.execute(query)
    conn.commit()

try:
    cursor.execute('DROP SCHEMA public CASCADE')
    conn.commit()
    cursor.execute('CREATE SCHEMA public')
    conn.commit()
    cursor.execute('GRANT ALL ON SCHEMA public TO postgres')
    conn.commit()
    cursor.execute('GRANT ALL ON SCHEMA public TO public')
    conn.commit()
except psycopg2.ProgrammingError as err:
    conn.rollback()
    cursor.execute('DROP owned by l3info_32')
    conn.commit()

for i in sql_schema.split(';'):
    try:
        cursor.execute(i)
        conn.commit()
    except psycopg2.ProgrammingError as err:
        # print("we caught the exception")
        conn.rollback()

create_nodes()
create_temporal_day()
create_routes()
create_combined()
create_stoproutename()
create_walk()
