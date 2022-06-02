import json
from enum import Enum


class PersistenceType(Enum):
    PICKLE = "pickle"
    POSTGRES = "postgres"


class Configuration:
    """
    Configuration class

    Args:
        raw_config (dict): The configuration dictionary.

    Attributes:
        persistence_type (PersistenceType): The persistence type.
        host (str): The hostname of the database.
        port (int): The port of the database.
        username (str): The username of the database.
        password (str): The password of the database.
        database (str): The database name.
        schema (str): The schema name.
    """

    supported_persistence = ["pickle", "postgres"]

    def __init__(self, raw_config):
        self.raw_config = raw_config
        if type(self.raw_config) is not dict:
            raise TypeError("Configuration must be a dictionary.")

        self._parse_config()

    def __repr__(self):
        return "<Configuration: {}>".format(self.config)

    def __str__(self):
        return json.dumps(self.raw_config, indent=4)

    def _parse_config(self):
        raw_config = self.raw_config

        self.bot_token = raw_config.get("bot_token", None)
        if "persistence" not in raw_config:
            raise KeyError("Persistence type not specified.")

        persistence = raw_config["persistence"].get("backend", "pickle")

        supported_persistences = set(item.value for item in PersistenceType)
        if persistence not in supported_persistences:
            raise ValueError(
                "Persistence type {} is not supported.".format(persistence)
            )

        self.persistence_type = PersistenceType(persistence)

        if self.persistence_type == PersistenceType.POSTGRES:
            self._set_postgres_config()

    def _set_postgres_config(self):
        db_config = self.raw_config["persistence"]

        self.host = db_config.get("postgres_host", "localhost")
        self.port = db_config.get("postgres_port", 5432)
        self.username = db_config.get("postgres_username", "postgres")
        self.password = db_config.get("postgres_password", "postgres")
        self.database = db_config.get("postgres_database", "niscoin")
        self.schema = db_config.get("postgres_schema", "public")

    def set_pickle_directory(self, pickle_path):
        self.pickle_path = pickle_path

    def get_connection_string(self):
        if self.persistence_type == PersistenceType.POSTGRES:
            return "postgresql://{}:{}@{}:{}/{}".format(
                self.username, self.password, self.host, self.port, self.database
            )
        else:
            return None
