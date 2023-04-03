sql_schema = """create table nodes (
stop_i numeric ,
lat numeric,
lon numeric,
name text,
PRIMARY KEY (stop_i)
);
create table routes(
route_type NUMERIC,
route_name TEXT,
route_i NUMERIC, 
PRIMARY KEY (route_i)
);
create table temporal_day(
from_stop_i numeric,
to_stop_i numeric,
dep_time_ut numeric,
arr_time_ut numeric,
route_type numeric ,
trip_i numeric,
seq numeric ,
route_i numeric,
PRIMARY KEY (from_stop_i, to_stop_i, dep_time_ut, arr_time_ut, trip_i)
);
create table walk (
from_stop_i numeric,
to_stop_i numeric,
d_walk numeric,
route_i text,
PRIMARY KEY (from_stop_i, to_stop_i)
);
create table combined(
from_stop_i numeric,
to_stop_i numeric,
duration_avg numeric,
route_i numeric references routes(route_i),
PRIMARY KEY (from_stop_i, to_stop_i, route_i)
);

create table combxwalk(
from_stop_i numeric,
to_stop_i numeric,
duration_avg numeric,
route_i text,

PRIMARY KEY  (from_stop_i, to_stop_i, route_i)
)
"""