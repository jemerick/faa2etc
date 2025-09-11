# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "click",
#     "requests",
# ]
# ///

import csv
import tempfile
import zipfile
from pathlib import Path

import click
import requests

FAA_DATABASE_URL = "https://registry.faa.gov/database/ReleasableAircraft.zip"

TYPE_REGISTRATION_MAP = {
    "1": "Individual",
    "2": "Partnership",
    "3": "Corporation",
    "4": "Co-Owned",
    "5": "Government",
    "7": "LLC",
    "8": "Non Citizen Corporation",
    "9": "Non Citizen Co-Owned",
}


def process_aircraft_reference_file(aircraft_reference_file_name) -> dict:
    """
    Reads the aircraft reference file which provides aircraft manufacturer, model, and type.
    """
    aircraft_reference = {}
    with open(aircraft_reference_file_name, "r", encoding="utf-8-sig") as aircraft_reference_file:
        aircraft_reader = csv.DictReader(aircraft_reference_file)
        with click.progressbar(aircraft_reader, label="Parsing aircraft reference data") as aircraft_reader_progress:
            for row in aircraft_reader_progress:
                code = row["CODE"]
                manufacturer = row["MFR"]
                model = row["MODEL"]
                aircraft_reference[code] = {
                    "manufacturer": manufacturer.strip(),
                    "model": model.strip(),
                }
    return aircraft_reference


def process_aircraft_registration_file(aircraft_registration_file_name) -> list[dict]:
    """
    Reads the aircraft registration file and returns a list of aircraft registration data as a dictionary.
    """
    aircraft_registrations = []
    with open(aircraft_registration_file_name, "r", encoding="utf-8-sig") as aircraft_registration_file:
        registration_reader = csv.DictReader(aircraft_registration_file)
        with click.progressbar(
            registration_reader, label="Parsing aircraft registration data"
        ) as registration_reader_progress:
            for row in registration_reader_progress:
                tail_number = row["N-NUMBER"]
                aircraft_reference_code = row["MFR MDL CODE"]
                year = row["YEAR MFR"]
                owner_name = row["NAME"]
                city = row["CITY"]
                state = row["STATE"]
                mode_s_hex = row["MODE S CODE HEX"]
                registrant_type_code = row["TYPE REGISTRANT"]
                registrant_type = TYPE_REGISTRATION_MAP.get(registrant_type_code) or "Unknown"

                registration_data = {
                    "tail_number": tail_number.strip(),
                    "aircraft_reference_code": aircraft_reference_code.strip(),
                    "year": year.strip(),
                    "owner_name": owner_name.strip(),
                    "city": city.strip(),
                    "state": state.strip(),
                    "mode_s_hex": mode_s_hex.strip(),
                    "registrant_type": registrant_type,
                }
                aircraft_registrations.append(registration_data)

    return aircraft_registrations


def create_emcomm_tools_file(aircraft_registrations, aircraft_reference, output_file):
    fieldnames = [
        "tail_number",
        "make",
        "model",
        "year",
        "owner_name",
        "city",
        "state",
        "mode_s_hex",
        "registrant_type",
    ]
    writer = csv.DictWriter(output_file, fieldnames=fieldnames, delimiter="|")
    writer.writeheader()

    with click.progressbar(
        aircraft_registrations, label="Creating ETC database file"
    ) as aircraft_registrations_progress:
        for aircraft_registration in aircraft_registrations_progress:
            aircraft_reference_code = aircraft_registration.pop("aircraft_reference_code", "")
            aircraft_reference_data = aircraft_reference.get(aircraft_reference_code)
            make = aircraft_reference_data["manufacturer"] if aircraft_reference_data else "Unknown"
            aircraft_registration["make"] = make
            model = aircraft_reference_data["model"] if aircraft_reference_data else "Unknown"
            aircraft_registration["model"] = model

            writer.writerow(aircraft_registration)


def download_database_file(database_url):
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_directory_name:
        temp_directory = Path(temp_directory_name)
        # Path to save the downloaded zip
        zip_path = zip_path = temp_directory / "database.zip"

        click.secho(f"Downloading {database_url} to {zip_path}")

        # Download the zip file
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
        }
        response = requests.get(database_url, stream=True, headers=headers)
        response.raise_for_status()  # raise error if download fails

        total_size = int(response.headers.get("Content-Length", 0))

        with (
            open(zip_path, "wb") as zip_file,
            click.progressbar(
                length=total_size, label="Downloading FAA database zip file", show_percent=True, show_pos=True
            ) as progress_bar,
        ):
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:  # filter out keep-alive chunks
                    zip_file.write(chunk)
                    progress_bar.update(len(chunk))

        # Extract the zip file
        with zipfile.ZipFile(zip_path, "r") as zip_file:
            file_list = zip_file.namelist()
            if "MASTER.txt" not in file_list:
                raise FileNotFoundError("MASTER.txt file not found in database zip file")
            if "ACFTREF.txt" not in file_list:
                raise FileNotFoundError("ACFTREF.txt file not found in database zip file")

            with click.progressbar(
                ["MASTER.txt", "ACFTREF.txt"], label="Extracting database zip file", show_percent=True
            ) as progress_bar:
                for file_name in progress_bar:
                    zip_file.extract(file_name, temp_directory)

        aircraft_reference_file = temp_directory / "ACFTREF.txt"
        aircraft_registration_file = temp_directory / "MASTER.txt"

        aircraft_reference = process_aircraft_reference_file(aircraft_reference_file)
        aircraft_registrations = process_aircraft_registration_file(aircraft_registration_file)

    return aircraft_reference, aircraft_registrations


@click.command()
@click.option("--database-url", default=FAA_DATABASE_URL, help="The URL to download the FAA database.")
@click.option("--registration-file", type=click.Path(exists=True), help="Registration file, ex MASTER.txt")
@click.option("--reference-file", type=click.Path(exists=True), help="Aircraft reference file, ex ")
@click.argument("output", type=click.File("w"))
def main(database_url, registration_file, reference_file, output) -> None:
    """
    Converts FAA registration data to simplified EmComm Tools formatted CSV.

    This script will default to the FAA database URL but another URL for the zip file can be provided
    using the --database-url option.

    Additionally, the registration and reference file can also just be directly provided using the
    --registration-file and --reference-file options together.

    uv run faa2etc.py faa.csv

    uv run faa2etc.py --registration-file MASTER.txt --reference-file ACFTREF.txt faa.csv
    """
    click.secho("Converting FAA data to ETC data format")

    if registration_file and reference_file:
        aircraft_reference = process_aircraft_reference_file(reference_file)
        aircraft_registrations = process_aircraft_registration_file(registration_file)
    else:
        aircraft_reference, aircraft_registrations = download_database_file(database_url)

    create_emcomm_tools_file(aircraft_registrations, aircraft_reference, output)

    click.secho("Success!", fg="green")


if __name__ == "__main__":
    main()
