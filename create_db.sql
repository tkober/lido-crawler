-- ====================================================================================================================
-- AIRPORTS
-- ====================================================================================================================
create table airports
(
	icao string not null constraint airports_pk primary key CHECK ( length(icao)=4 ),
	iata string,
	latest_information integer not null REFERENCES airport_information(id)
);

create unique index airports_iata_uindex
	on airports (iata);

create index airports_icao_index
	on airports (icao);


-- ====================================================================================================================
-- AIRPORT INFORMATION
-- ====================================================================================================================
create table airport_information
(
    id integer not null constraint airport_information_pk primary key autoincrement,
    icao string not null REFERENCES airports(icao),
    nav_data_airport_id string not null,
    country string not null,
	city string not null,
    name string not null,
    latitude string not null,
    longitude string not null,
    elevation integer not null,
    longest_runway integer not null,
    timestamp date not null
);

create unique index airport_information_id_uindex
	on airport_information (id);

create unique index airport_information_nav_data_airport_id_uindex
	on airport_information (nav_data_airport_id);


-- ====================================================================================================================
-- CHARTS
-- ====================================================================================================================
create table charts
(
    id integer not null constraint charts_pk primary key autoincrement,
    airport_information integer not null REFERENCES airport_information(id),
    nav_data_chart_id string not null,
    type string not null,
    name string not null,
    geo_chart integer not null,
    chart_binary integer not null REFERENCES chart_binaries(id)
);

create unique index charts_id_uindex
	on charts (id);

create unique index charts_nav_data_chart_id_uindex
	on charts (nav_data_chart_id);


-- ====================================================================================================================
-- CHART BINARIES
-- ====================================================================================================================
create table chart_binaries
(
    id integer not null constraint chart_binaries_pk primary key autoincrement,
    mime_type string not null,
    creation_date date not null,
    data blob not null
);

create unique index chart_binaries_id_uindex
    on chart_binaries (id);