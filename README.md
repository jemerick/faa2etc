# FAA to ETC

A python script to convert the FAA's [Releasable Aircraft Database Download](https://www.faa.gov/licenses_certificates/aircraft_certification/aircraft_registry/releasable_aircraft_download) to a simple format for [EmComm Tools Community](https://community.emcommtools.com/) (ETC).

The FAA database is refreshed daily at 11:30 pm central time. 

This script simplifies the data to only what ETC requires from the Aircraft Registration Master file (`MASTER.txt`) and the Aircraft Reference file by Make/Model/Series Sequence (`ACFTREF.txt`).

The pipe `|` deliminated output file contains the following fields:

* `tail_number` - Identification number assigned to aircraft.
* `make` - Name of the aircraft manufacturer.
* `model` - Name of the aircraft model and series.
* `year` - The year the aircraft was manufactured.
* `owner_name` - The first registrant’s name which appears on the Application for Registration, AC Form 8050-1.
* `city` - The city name which appears on the Application for Registration, AC Form 8050-1 or the latest address reported.
* `state` - The state name which appears on the Application for Registration, AC Form 8050-1 or the latest address reported.
* `mode_s_hex` - Mode S Code in Hexidecimal Format. The Mode S code (also called the ICAO 24-bit aircraft address) is a unique 24-bit hexadecimal identifier assigned to each aircraft's transponder.
* `registrant_type` - The type of aircraft registration. One of the following values `Individual`, `Partnership`, `Corporation`, `Co-Owned`, `Government`, `LLC`, `Non Citizen Corporation`, `Non Citizen Co-Owned`, `Unknown`


By default, the script will automatically download the FAA database zip file and create the ETC database file. Additionally, another URL to download the FAA database zip file can be provided. Alternatively, the two necessary files listed above can be provided directly.

## Usage

`uv run faa2etc.py faa.csv`

`uv run faa2etc.py --database-url "https://registry.faa.gov/database/ReleasableAircraft.zip" faa.csv`

`uv run faa2etc.py --registration-file MASTER.txt --reference-file ACFTREF.txt faa.csv`
