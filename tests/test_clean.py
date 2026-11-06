import json
def test_valid_json_kept():
    obj = json.loads('{"intent": "alarm_set", "date": "tomorrow", "time": null, "place": null}')
    assert set(obj.keys()) == {"intent", "date", "time", "place"}
    assert obj["intent"] in {"alarm_set","alarm_query","calendar_set","calendar_query","calendar_remove","weather_query","datetime_query","recommendation_events"}
def test_slot_must_appear_in_command():
    text = "set an alarm for seven thirty am tomorrow"
    assert "seven thirty am" in text
    assert "london" not in text
