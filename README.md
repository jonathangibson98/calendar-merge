# Calendar Merge

Combine as many calendars as you want into one. Make as many merged calendars as you want.

Say you have personal, work, and family calendars, plus a bunch of sports team calendars. Make one merged calendar called **All Calendars** and another called **Sports**. Each one becomes its own calendar entity that works with any calendar card, plus a sensor that lists the upcoming events.

No YAML. No AppDaemon. Everything is set up from the Home Assistant UI.

## Features

- **Unlimited groups.** Each group is its own device with its own calendars and settings
- **Works with any calendar** in Home Assistant: Google, CalDAV, Outlook, local calendars, ICS feeds, sports team calendars, and so on
- **A real calendar entity** per group, so it works with the built-in Calendar dashboard, the Calendar card, and third-party calendar cards that browse by month or week
- **An "Upcoming events" sensor** per group with every event in the next X days as attributes, for custom cards and templates
- **Duplicate removal** (optional) when the same event is on more than one calendar
- **Handles all-day events**, multi-day events, and mixed time zones
- **Keeps working if one source calendar fails.** The rest still show up
- **Edit anytime.** Add or remove calendars from a group without deleting it

## Installation

### HACS (custom repository)
1. Open **HACS** in Home Assistant
2. Three-dot menu, then **Custom repositories**
3. Add `https://github.com/YOUR-USERNAME/calendar-merge` with the category **Integration**
4. Search for **Calendar Merge**, download it, and **restart Home Assistant**

### Manual
Copy the `custom_components/calendar_merge` folder into your `/config/custom_components/` folder and restart Home Assistant.

## Setup

1. Go to **Settings > Devices & services > Add integration**
2. Search for **Calendar Merge**
3. Fill in the form:
   - **Name**: for example `All Calendars` or `Sports`
   - **Calendars to merge**: pick two or more calendars
   - **Days ahead**: how far ahead the sensor looks (default 30)
   - **Update interval**: how often to re-read your calendars, in minutes (default 60)
   - **Remove duplicate events**: show an event once if it's on more than one calendar
4. Repeat steps 1 to 3 for every group you want

To change a group later, go to **Settings > Devices & services > Calendar Merge**, then click the gear icon on the group.

## What you get

For a group named **Sports**:

| Entity | What it is |
|---|---|
| `calendar.sports` | The merged calendar. Use it in any calendar card |
| `sensor.sports_upcoming_events` | Number of upcoming events, with the full list in its attributes |

### Sensor attributes

| Attribute | Description |
|---|---|
| `events` | List of upcoming events, sorted by start time |
| `event_count` | Number of events in the list |
| `days_ahead` | How far ahead it's looking |
| `calendars` | The source calendars in this group |
| `last_updated` | When the calendars were last read |

Each item in `events` has: `summary`, `start`, `end`, `all_day`, `description`, `location`, and `calendar` (the source calendar it came from).

### Example: show the next 5 events in a Markdown card

```yaml
type: markdown
content: >
  {% for e in state_attr('sensor.sports_upcoming_events', 'events')[:5] %}
  **{{ e.summary }}**  
  {{ as_datetime(e.start).strftime('%a %b %-d, %-I:%M %p') if not e.all_day else e.start }}  
  {% endfor %}
```

## Good to know

- Calendars are re-read on the update interval. A new event on a source calendar can take up to that long to appear in the **sensor**. Calendar cards that browse by date read your calendars fresh each time
- A group can't include itself, but a group **can** include another merged group
- If you restart Home Assistant and a source calendar isn't ready yet, the group waits and retries on its own
- The sensor's event list is kept out of the recorder database so it won't bloat your history

## Moving from the AppDaemon version

If you were using a `CalendarMerge` AppDaemon app with `sensor.merged_calendar`, the new sensor has the same `events` attribute format. Point your cards at `sensor.<group name>_upcoming_events` instead and you can delete the AppDaemon app.

## Contributing

Bug reports and pull requests are welcome. Open an issue and include what calendars you're merging and any warnings from **Settings > System > Logs**.
