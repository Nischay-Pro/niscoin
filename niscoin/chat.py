import copy


CONFIGURATION_VERSION = 1


class ChatConfiguration:
    def __init__(self):
        self.configuration = {
            "reputation": {
                "enabled": True,
                "adminOnly": False,
                "ignorelist": [],
                "filters": {
                    "minipositive": {
                        "base": [".+", "miniplus", "mini+", "dotplus", "dp"],
                        "custom": [],
                        "enabled": True,
                    },
                    "positive": {
                        "base": ["+", "+1", "plus"],
                        "custom": [],
                        "enabled": True,
                    },
                    "megapositive": {
                        "base": ["++", "+2", "megaplus", "mega+"],
                        "custom": [],
                        "enabled": True,
                    },
                    "mininegative": {
                        "base": [".-", "miniminus", "mini-", "dotminus", "dm"],
                        "custom": [],
                        "enabled": True,
                    },
                    "negative": {
                        "base": ["-", "-1", "minus"],
                        "custom": [],
                        "enabled": True,
                    },
                    "meganegative": {
                        "base": ["--", "-2", "megaminus", "mega-"],
                        "custom": [],
                        "enabled": True,
                    },
                },
            },
            "lottery": {
                "enabled": True,
                "odds": 200,
                "multiplier": 10,
            },
            "translation": {
                "enabled": True,
                "cost": 50,
            },
            "coins": {
                "enabled": True,
                "exchangeRate": 10,
            },
            "initiated": False,
            "configuration_version": CONFIGURATION_VERSION,
        }
        self.user_data = {}

    def __repr__(self) -> str:
        return str(self.configuration)

    def get(self, key):
        return self.configuration[key]

    def as_dict(self):
        configuration = {
            "configuration": self.configuration,
            "user_data": self.user_data,
        }
        return configuration


def user_template(user_id: int) -> dict:
    return {
        "xp": 0,
        "coins": 0,
        "rep": 0,
        "last_message": 0,
        "delta_award_time": 0,
    }


def check_migration(configuration):
    if configuration.get("configuration_version") < CONFIGURATION_VERSION:
        return True
    return False


def from_dict(configuration):
    new_configuration = ChatConfiguration()
    new_configuration.configuration = configuration["configuration"]
    new_configuration.user_data = configuration["user_data"]
    return new_configuration


legacy_carry_forward_keys = [
    "xp",
    "rep",
    "coins",
    "last_message",
    "delta_award_time",
]


def migrate_legacy_user_data(old_user_data, new_configuration):
    new_configuration.user_data = old_user_data["users"]
    temp = copy.deepcopy(new_configuration.user_data)
    for user in temp:
        for user_item in temp[user].keys():
            if user_item not in legacy_carry_forward_keys:
                del new_configuration.user_data[user][user_item]
    if "init" in old_user_data.keys():
        new_configuration.configuration["initiated"] = old_user_data["init"]
    return new_configuration


def migrate_configuration(old_configuration):
    old_version = old_configuration.get("configuration_version")
    if old_version is None:
        return ChatConfiguration
    elif old_version == CONFIGURATION_VERSION:
        return old_configuration
    elif old_version > CONFIGURATION_VERSION:
        raise Exception("Configuration version is too new.")
    else:
        raise Exception("Unknown configuration version")
