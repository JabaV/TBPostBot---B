import os
import pickle
import random
import re
from datetime import datetime, timedelta
from random import randint
from time import sleep
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union, cast
import vk_api
from dotenv import load_dotenv

from modules import module_logger

# загрузка переменных окружения из .env
load_dotenv()

skip = 0
# поддерживаем оба варианта имени, но приоритет у верхнего регистра
token = os.environ.get("TOKEN") or os.environ.get("token")
if not token:
    raise RuntimeError("VK API token is missing. Define TOKEN in .env or environment.")

# дефолтная пауза между постами, если не указана в groups.txt
wait_time: int = int(os.environ.get("DEFAULT_WAIT_TIME"))

max_blocks: int = int(os.environ["MAX_BLOCKS"])

vk_session = vk_api.VkApi(token=token)
vk = vk_session.get_api()
bot_id = vk.users.get()[0]["id"]


time_dict: Dict[int, datetime] = {}
tgtg: int = 0

picks = [457239111, 457239115, 457239116, 457239118, 457239119]


def post(_target_group: int, _text: str, _image: Optional[int]) -> None:
    if _image is None:
        vk.wall.post(owner_id=-_target_group, message=_text)
    else:
        vk.wall.post(
            owner_id=-_target_group,
            message=_text,
            attachments=f"photo{bot_id}_{_image}",
        )


def parse_duration(spec: str) -> int:
    if not spec:
        return wait_time
    pattern = r"((?P<d>\d+)d)?((?P<h>\d+)h)?((?P<m>\d+)m)?((?P<s>\d+)s)?"
    m = re.fullmatch(pattern, spec.strip())
    if not m:
        module_logger.eLog(f"Bad delay format '{spec}', using default wait_time")
        return wait_time
    days = int(m.group("d") or 0)
    hours = int(m.group("h") or 0)
    mins = int(m.group("m") or 0)
    secs = int(m.group("s") or 0)
    return days * 86400 + hours * 3600 + mins * 60 + secs


def load_file(path: str) -> List[str]:
    parts: List[str] = []
    if not os.path.exists(path):
        return parts
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        parts = content.split("---")
        for x in range(len(parts)):
            parts[x] = parts[x].strip("\n")
    return parts


def pick_variant(variants: List[str], desired: Optional[str]):
    if not variants:
        return ""
    if desired is not None or desired != "-":
        for vid in variants:
            pref_id = vid.find("|")
            if vid[:pref_id] == desired:
                return vid[pref_id + 1 :]
    vid = random.choice(variants)
    return vid[vid.find("|") + 1 :]


def build_text(desirements: Optional[List[str]]):
    result = ""
    tags = load_file("files/tags.txt")
    tags = pick_variant(tags, desirements[0]) if desirements else random.choice(tags)
    result += tags[tags.find("|") + 1 :] + "\n"
    blocks_amount = max_blocks
    for i in range(1, blocks_amount):
        variants = load_file(f"files/block{i}.txt")
        variants = (
            pick_variant(variants, desirements[i])
            if desirements[i] != "-"
            else random.choice(variants)
        )
        if variants.__contains__("|"):
            variants = variants[variants.find("|") + 1 :]
        result += variants + "\n"
    result += "@topbossfights"
    return result, blocks_amount


def parse(data: str) -> Tuple[str, str, Optional : List[str]]:
    has_desirements = data.find("[") > -1
    _timer = None
    _group, _timer = data[: data.find(":")], data[data.find("|") + 1 :]
    if has_desirements:
        des_list = data[data.find("[") + 1 : data.find("]")].split(":")
        if des_list.count("-") == max_blocks + 1:
            des_list = None
    else:
        des_list = None
    return _group, _timer, des_list


VKPost = Mapping[str, Any]
MaybePost = Union[VKPost, None, int]


def get_last_post(_tg: int, wt: int) -> MaybePost:
    last_post = None
    try:
        count = 2
        while count:
            posts = vk.wall.get(
                owner_id="-" + str(_tg), offset=0 if count == 2 else 100, count=100
            )["items"]
            if len(posts) < 1:
                module_logger.Log(
                    f"No posts found in group {_tg} (offset {0 if count == 2 else 100})"
                )
                return None
            if wt == 1:
                for x in posts:
                    if x.get("from_id") == bot_id:
                        last_post = x
                        break
            elif wt in (2, 3):
                for x in posts:
                    if x.get("signer_id") == bot_id:
                        last_post = x
                        break
            if last_post is None:
                count -= 1
            else:
                module_logger.Log(f"Last bot-related post found in group {_tg}")
                return last_post
        return last_post
    except Exception as e:
        module_logger.eLog(f"get_last_post({_tg}) failed: {e}")
        return -1


def check_suggests(_tg: int, time_s: int) -> int:
    try:
        suggested_posts = vk.wall.get(owner_id=-_tg, filter="suggests")
    except Exception as e:
        module_logger.eLog(f"check_suggests({_tg}) get suggests failed: {e}")
        return -1

    last_pst = get_last_post(_tg, 2)
    if len(suggested_posts.get("items", [])) < 1:
        if _tg in time_dict:
            if datetime.now() - time_dict[_tg] >= timedelta(seconds=time_s):
                module_logger.Log(
                    f"Suggest empty and time exceeded in group {_tg} — ready to post"
                )
                return 1
            else:
                return 0
        elif last_pst is not None:
            if last_pst != -1:
                lp = cast(VKPost, last_pst)
                if datetime.now() - datetime.fromtimestamp(lp["date"]) >= timedelta(
                    seconds=time_s
                ):
                    module_logger.Log(
                        f"Last post older than threshold in group {_tg} — ready to post"
                    )
                    return 1
                else:
                    return 0
            else:
                return -1
        else:
            if _tg in time_dict:
                if datetime.now() - time_dict[_tg] >= timedelta(seconds=time_s):
                    return 1
                else:
                    return 0
            else:
                return 1
    suggest_time = suggested_posts["items"][0]["date"]
    if datetime.now() - datetime.fromtimestamp(suggest_time) >= timedelta(
        seconds=time_s
    ):
        module_logger.Log(
            f"Suggest older than threshold in group {_tg} — ready to post"
        )
        return 1
    return 0


if __name__ == "__main__":
    while True:
        try:
            with open("files/groups.txt", "r", encoding="utf-8") as file:
                module_logger.Log("STARTING FULL CYCLE")
                while True:
                    string = file.readline()
                    if not string:
                        break
                    # Комментарии: пропускаем строки, начинающиеся с "#"
                    if string.lstrip().startswith("#"):
                        continue
                    if skip == 1:
                        skip = 0
                        continue
                    target_group, timer, template_meta = parse(string)
                    tgtg = target_group
                    timer = parse_duration(timer)
                    text, amount = build_text(template_meta)
                    image = random.choice(picks) if random.randint(1, 4) == 4 else None
                    time_dict = {}
                    with open("files/dumping.pkl", "rb+") as _p:
                        if os.stat("files/dumping.pkl").st_size != 0:
                            time_dict = pickle.load(_p)
                    module_logger.Log(f"Now working with group {target_group}")

                    group = vk.groups.getById(
                        group_id=target_group, fields="wall, activity"
                    )
                    is_banned = (
                        1
                        if str(group[0]["activity"]).startswith("Данный материал")
                        else 0
                    )
                    if is_banned:
                        module_logger.Log(
                            f"Group {target_group} is banned by RCW, please remove such entry from list"
                        )
                        continue
                    wall_type = group[0]["wall"]
                    module_logger.Log("Got the wall type")

                    if wall_type == 2 or wall_type == 3:
                        should_post = check_suggests(
                            target_group, wait_time if timer is None else timer
                        )
                        module_logger.Log(
                            f"Should I post in group {target_group}? result={should_post}"
                        )
                        if should_post == 1:
                            module_logger.Log("Decision: post now (suggest mode)")
                            vk.account.setOnline()
                            post(target_group, text, image)
                            time_dict[target_group] = datetime.now()
                            module_logger.Log("Posted and saved time")
                            try:
                                with open("files/dumping.pkl", "wb+") as p:
                                    pickle.dump(time_dict, p)
                            except Exception as e:
                                module_logger.eLog(f"Failed to save dumping.pkl: {e}")
                        if should_post == -1:
                            module_logger.Log(
                                "Decision: do not post due to error state"
                            )
                            vk.account.setOffline()
                            sleep(randint(30, 468))
                            continue
                    elif wall_type == 1:
                        temp_time = wait_time if timer is None else timer
                        module_logger.Log(f"Choosed time to post: {temp_time}s")
                        last_bot_post = get_last_post(target_group, wall_type)
                        if last_bot_post is None:
                            module_logger.Log(
                                "Can't find my post! Posting right now..."
                            )
                            vk.account.setOnline()
                            post(target_group, text, image)
                        elif last_bot_post != -1:
                            module_logger.Log("Found a post, evaluating time threshold")
                            post_time = cast(VKPost, last_bot_post)["date"]
                            if datetime.fromtimestamp(
                                post_time
                            ) <= datetime.now() - timedelta(seconds=temp_time):
                                module_logger.Log("Threshold passed — posting")
                                vk.account.setOnline()
                                post(target_group, text, image)
                        elif last_bot_post == -1:
                            module_logger.Log(
                                "My job here is done (error in get_last_post)"
                            )
                            vk.account.setOffline()
                            sleep(randint(30, 468))
                            continue
                    vk.account.setOffline()
                    module_logger.Log("Sleep for next iteration")
                    sleep(5)
                sleep(parse_duration("6h"))
                module_logger.Log("FULL ITERATION PAST")
        except Exception as e:
            module_logger.eLog(str(tgtg) + " " + str(e))
            sleep(60)
            skip = 1
