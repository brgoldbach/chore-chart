# Chore Chart

Keep the household chore list in Home Assistant. Print a one-page sheet each month and cross chores off by hand.

## Install

1. Go to **Settings > Apps > Install app**.
2. In the top-right menu, select **Repositories**.
3. Add `https://github.com/brgoldbach/chore-chart`.
4. Select **Chore Chart**, then **Install**.
5. On the **Info** tab, turn on **Show in sidebar**, then select **Start**.

Home Assistant offers each new version as an update.

To run your own changes, copy the `chore_chart` folder into the `local_apps` share (Samba) or into `/local_apps` (SSH) instead. It then shows under **Local apps**. A local copy and the repository version are separate apps with separate data. To move your chores between them, use **Export chores** and **Import chores**.

## First setup

Do these steps on the app's **Settings** tab.

1. Under **Owners**, add the people who do chores.
2. Under **Printer**, select **Search for printers**, then **Use** next to your printer.
3. Select **Print now** to test the printer.
4. Under **Auto-print**, turn on printing for the 1st of each month, and set the time.

The search finds printers with driverless printing: AirPrint, IPP Everywhere, or Mopria. Most current network printers support one of these. The app keeps the printer's network name, not its IP address, so printing still works after the IP changes. If the search does not find your printer, select **Enter an address instead**, for example `ipp://192.168.1.50/ipp/print`.

## Daily chores

Under **Daily** on the **Chores** tab, add the routines you do every day, for example "Load the dishwasher". They print as a list at the top of the sheet. They have no boxes, owners, or time estimates, and they do not count toward anyone's load. Edit a name in the list to change it.

## Chores

On the **Chores** tab, select **Add chore**. To change a chore, select it in the list. To make a similar chore, open one and select **Duplicate**: a copy named "… (copy)" opens, and it is saved only when you select **Save**.

Above the list:

| Control | Does |
|---|---|
| Search | Shows the chores whose name or note contains the text. |
| Owner filter | Shows the chores of one person (including turns and shared chores), Shared chores, or chores with No owner. |
| Interval filter | Shows the chores that repeat in weeks, months, or years. |
| Sort | Name, Owner (in Owners-list order), Most often, or Most time per month. |

Each chore's summary shows its time per occurrence and its approximate time per month, for example "30 min each · ≈ 2 h 10 m a month". For a chore with a season, the monthly time applies to the months in its season.

| Field | Meaning |
|---|---|
| Chore | What to do. |
| Owners | Who does it. Check no one for a chore without an owner. |
| Take turns / Shared | Shows when you check 2 or more people. **Take turns**: each time the chore is due, it goes to the next person. The person in **starting with** does it in the aligned month. **Shared**: everyone checked does it together, and its time splits evenly between them. |
| Every | Interval in weeks, months, or years. |
| Day | Week chores only. The weekday the chore happens on, for example Tuesday, or **Any day**. |
| Aligned to | Any month in which the chore is due. For a week chore with a day, the first of those days in the aligned month starts the rhythm. |
| Minutes | Optional time estimate. The app uses it for each person's load. |

The schedule repeats in both directions from the aligned month. Example: every 3 months aligned to November is due in February, May, August, and November.

Under **More**:

| Field | Meaning |
|---|---|
| Season | Months when the chore applies, for example Apr to Oct. The range can cross the new year (Nov to Mar). Turns keep counting through the months outside the season. |
| Note | Short text, printed under the chore name. |

## Owners

On the **Settings** tab, under **Owners**:

- Edit a name to rename the person. All their chores change with it, including turns and shared chores.
- The sheet lists the owner sections in the order you added the owners.
- ✕ removes an owner. You can remove an owner only after you reassign or delete their chores.

## The sheet

- The sheet has one section per owner, then **Shared**, then **No owner** (only when it has chores).
- Each corner of the printout has a small decoration that changes with the month. It stays in the margin, and it prints as light gray on a black-and-white printer.

  | Month | Theme |
  |---|---|
  | January, February | Winter: snowflakes |
  | March to May | Spring: a flower and a leafy vine |
  | The month of Easter (March or April; the app works out the date each year) | Easter: an egg and pastel dots |
  | June, August | Summer: a sun and waves |
  | July | 4th of July: fireworks and stars |
  | September | Fall: maple leaves on a twig |
  | October | Halloween: a jack-o'-lantern, and a curling pumpkin vine with a bat and a small jack-o'-lantern |
  | November | Thanksgiving: a pumpkin and wheat |
  | December | Christmas: holly with berries, and a string of lights |
- On the printout, each section runs the full width of the page, with its chores two to a line. On a fuller month, the text shrinks. If the page still runs out, a section continues on the next page under "Name (cont.)".
- The printout shows the boxes and the chore name. It leaves out how often a chore repeats; the **Sheet** tab still shows that.
- Each owner heading shows that person's load, including their part of shared chores. The Shared heading shows the total shared time.
- A chore with turns appears in each person's section, with only that person's boxes.
- A week chore gets one box per due date, labelled with the day of the month. Each date belongs to the month that contains it.
  - **With a day**, for example Tuesday: each box falls on that day. A Tuesday on December 1 goes on December's sheet, even when the rest of its week is in November. The Sheet tab shows the day, for example "2 weeks · Tue".
  - **Any day**: each box stands for the week from Monday, and the label is that Monday's date.
- Each section ends with 4 blank spaces (2 lines) for write-ins. With an odd number of chores, the section gets 5, so its last line is full.
- **Extra** fills the rest of the page with full-width write-in rows: a line for the chore and a line for who does it.
- With 3 owners, Letter paper holds about 30 chores at full size, and about 55 on one page with smaller text (6 daily chores take the space of about 6 chores). Past that, the sheet continues on page 2, and the app shows a warning.
- The **Sheet** tab shows the same chores, without the empty sections. You can tap a box there to check it off. A reprint shows checked boxes with ✓. The paper sheet works without this.

## Year tab

The Year tab covers the 12 months from the selected month.

| View | Shows |
|---|---|
| **Hours** | Each person's hours per month and for the year. Darker cells are heavier months. Tap a month to open its sheet. Tap a person to see their chores in the Calendar. |
| **Calendar** | Who does each chore in each month: a short name (for example Br, Be, A), "Sh" for shared, or "4×" for a week chore. Filter by person or Shared. |

To re-balance:

- **◀ ▶** next to a chore in the Calendar move its aligned month one month earlier or later. They show for chores that repeat every 2 months or less often.
- Tap a chore name to change its owners or turns. Use the **Year** column in Hours to compare people.

## Backup

On the **Settings** tab:

- **Export chores** downloads `chore-chart.json` with your owners, daily chores, and chores. It leaves out the printer settings and check-offs.
- **Import chores** replaces your owners, daily chores, and chores with the ones in a file, after you confirm.

Older files import too: fields that a file does not have get their default values. A file without daily chores leaves your current daily list as it is.

## Network access

The app uses the host network, because printer search needs mDNS (Bonjour) on your LAN. Home Assistant shows a lower security rating for this. The app accepts requests only from Home Assistant's ingress, so other devices on the LAN cannot open it. Avahi in the app only searches. It does not announce any names on your LAN.

## Data

The app keeps its data in `/data`: `chores.json`, `owners.json`, `daily.json`, `done.json` (check-offs), and `settings.json`. Home Assistant backups include it. If two people edit the same chore at the same time, the last save wins.

New versions of the app read the data of older versions. Each new chore field has a default value (`CHORE_DEFAULTS` in `app/server.py`), so you never re-enter chores after an update.
