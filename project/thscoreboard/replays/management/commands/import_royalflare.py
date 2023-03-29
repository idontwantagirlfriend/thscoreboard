from django.core.management.base import BaseCommand, CommandParser
from datetime import datetime
import json
from pathlib import Path

import pytz
from replays import constant_helpers
from replays import replay_parsing
from replays import create_replay
from replays import limits
from replays import models


ROYALFLARE_JSON_DIRECTORY_PATH = Path(__file__).parent / "resources" / "royalflare"
REPLAY_DIRECTORY_PATH = Path("C:/Users/Markus/Downloads")


class Command(BaseCommand):
    help = """Import royalflare replays. To use this, you must first download and 
    extract royalflare replays from https://maribelhearn.com/mirror/royalflare.zip.
    Then, run this command with an argument pointing to the /replays folder you just
    made. The script imports those replays, using additional data from jsons that
    were downloaded from
    https://github.com/MaribelHearn/maribelhearn.com/tree/master/assets/games/royalflare/json
    """

    def add_arguments(self, parser: CommandParser) -> None:
        super().add_arguments(parser)

        parser.add_argument(
            "replay_dir",
            help="The directory containing the replays. Should end in /replays.",
        )

    def handle(self, *args, **options):
        print(ROYALFLARE_JSON_DIRECTORY_PATH)
        main(options["replay_dir"])


def main(replay_dir: str) -> None:
    json_files = ROYALFLARE_JSON_DIRECTORY_PATH.glob("**/*.json")
    for json_file in json_files:
        with open(json_file, encoding="utf-8") as f:
            all_replay_infos_from_json = json.load(f)
            for info_from_json in all_replay_infos_from_json:
                import_royalflare(info_from_json, Path(replay_dir))


def import_royalflare(info_from_json: dict, replay_dir: Path) -> None:
    comment = info_from_json["comment"]
    replay_path = parse_replay_path_from_json(replay_dir, info_from_json["replay"])
    created_timestamp = parse_timestamp_from_json(info_from_json["date"])
    imported_username = info_from_json["player"]

    try:
        if replay_path.stat().st_size > limits.MAX_REPLAY_SIZE:
            raise limits.FileTooBigError()
        replay_bytes = replay_path.read_bytes()
        if constant_helpers.CheckReplayFileDuplicate(replay_bytes):
            raise Exception("This replay already exists")
        replay_info = replay_parsing.Parse(replay_bytes)
        temp_replay = models.TemporaryReplayFile(user=None, replay=replay_bytes)
        temp_replay.save()

        create_replay.PublishNewReplay(
            user=None,
            difficulty=replay_info.difficulty,
            score=replay_info.score,
            category=1,
            comment=comment,
            is_good=True,
            is_clear=True,
            no_bomb=False,
            miss_count=None,
            video_link="",
            temp_replay_instance=temp_replay,
            replay_info=replay_info,
            created_timestamp=created_timestamp,
            imported_username=imported_username,
        )
    except Exception as e:
        if str(e) != "This replay already exists":
            print(f"Failed to import {replay_path}")
            print(e)


def parse_replay_path_from_json(replay_directory: Path, replay_location: str) -> Path:
    path_including_top_level_dir = Path(replay_location.lstrip("/"))
    path = Path(*path_including_top_level_dir.parts[1:])
    return replay_directory / path


def parse_timestamp_from_json(timestamp: str) -> datetime:
    if timestamp.count(":") == 2:
        unaware_datetime = datetime.strptime(timestamp, "%Y/%m/%d %H:%M:%S")
    elif ":" in timestamp:
        unaware_datetime = datetime.strptime(timestamp, "%Y/%m/%d %H:%M")
    else:
        unaware_datetime = datetime.strptime(timestamp, "%Y/%m/%d")
    aware_datetime = pytz.utc.localize(unaware_datetime)
    return aware_datetime
