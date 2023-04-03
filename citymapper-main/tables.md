So far I would say:

- **nodes**: stop_i
- **routes**: route_i
- **route_rps** : route_i -> routes where route_i = min(route_i) : foreign keys, relation 0..1 between route_rps and route_i
- **walk** : (from_stop_i, to_stop_i) -> NOT foreign keys from **nodes**  also route_i serves no purpose since walking routes have no actual id
- **short_walk** : (from_stop_i, to_stop_i) -> walk where d < 300 -> foreign keys
- **combined** : (from_stop_i, to_stop_i, route_i) -> we can go from one stop to another with multiple routes, NOT foreign keys from nodes and routes
-- **stopxroute** : (stop_i, route_i) -> associates a stop with all its routes, no foreign keys because stop_i and route_i are not unique
- **stoproutename** : (stop_i, route_name) -> takes stops from combined and names from (stopxroute inner join nodes inner join routes), no foreign keys because of the join
-- **combxwalk** : (from_stop_i, to_stop_i, route_i) -> concatenation of walk x combined, can't make foreign keys because of that
- **temporal_day**: (from_stop_i, to_stop_i, dep_time_ut, arr_time_ut, seq, route_i) -> same
- **super_route_comb** : (from_stop_i, to_stop_i, route_rps_i) , the keys from this table are not foreign keys because table is result of join from routexsuper and combined
- **routexsuper** : (route_i) permet de retrouver route_rps_i



SELECT stop_i, route_i into stopxroute
            FROM
            ((SELECT from_stop_i as stop_i, route_i
            FROM combined)
            UNION
            (SELECT to_stop_i as stop_i, route_i
            FROM combined)) as yes"