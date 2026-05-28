from pathlib import Path


def test_creates_data_folder_and_files(tmp_path: Path) -> None:
    from services.storage import Storage

    data = tmp_path / "fresh"
    Storage(data)
    assert (data / "telegram_chats.json").exists()
    assert (data / "influencers.json").exists()


def test_add_chat_persists(storage) -> None:
    assert storage.add_chat(111, "Test Group", "supergroup") is True
    assert storage.get_chat_ids() == [111]

    from services.storage import Storage
    reopened = Storage(storage.data_folder)
    assert reopened.get_chat_ids() == [111]


def test_add_chat_duplicate_returns_false(storage) -> None:
    storage.add_chat(111, "x", "group")
    assert storage.add_chat(111, "x", "group") is False
    assert len(storage.get_chats()) == 1


def test_remove_chat(storage) -> None:
    storage.add_chat(111, "x", "group")
    assert storage.remove_chat(111) is True
    assert storage.get_chat_ids() == []
    assert storage.remove_chat(111) is False


def test_chat_id_normalized_to_int(storage) -> None:
    storage.add_chat("123", "x", "group")
    assert storage.get_chat_ids() == [123]


def test_add_channel(storage) -> None:
    assert storage.add_channel("PewDiePie", "UC-lHJZR3Gqxm24_Vd_AJ5Yw") is True
    channels = storage.get_channels()
    assert len(channels) == 1
    assert channels[0]["id"] == "UC-lHJZR3Gqxm24_Vd_AJ5Yw"
    assert channels[0]["name"] == "PewDiePie"


def test_add_channel_duplicate(storage) -> None:
    storage.add_channel("PewDiePie", "UC-lHJZR3Gqxm24_Vd_AJ5Yw")
    assert storage.add_channel("Other", "UC-lHJZR3Gqxm24_Vd_AJ5Yw") is False


def test_remove_channel(storage) -> None:
    storage.add_channel("PewDiePie", "UC-lHJZR3Gqxm24_Vd_AJ5Yw")
    assert storage.remove_channel("UC-lHJZR3Gqxm24_Vd_AJ5Yw") is True
    assert storage.get_channels() == []
    assert storage.remove_channel("UC-lHJZR3Gqxm24_Vd_AJ5Yw") is False


def test_get_channel_by_id(storage) -> None:
    storage.add_channel("PewDiePie", "UC-lHJZR3Gqxm24_Vd_AJ5Yw")
    found = storage.get_channel("UC-lHJZR3Gqxm24_Vd_AJ5Yw")
    assert found is not None
    assert found["name"] == "PewDiePie"
    assert storage.get_channel("UC_unknown_") is None


def test_channel_id_trimmed(storage) -> None:
    storage.add_channel("X", "  UC-lHJZR3Gqxm24_Vd_AJ5Yw  ")
    assert storage.get_channel("UC-lHJZR3Gqxm24_Vd_AJ5Yw") is not None
