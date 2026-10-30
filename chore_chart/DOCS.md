# Chore Chart

Keep the household chore list in Home Assistant. Print a one-page sheet each month and cross chores off by hand.

## Scope

The app is built around the printed sheet. It does not yet use the rest of Home Assistant. Later work could make it a fuller Home Assistant app, for example:

- notifications when chores are due or overdue;
- owners linked to Home Assistant users, so each person sees and checks off their own chores;
- entities for dashboards and automations.

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
5. Optionally, under **Printout**, choose a layout (see [Layouts](#layouts)).

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

- Edit a name to rename the person. All their chores change with it, including turns and shared chores, and so does their color.
- Pick each person's printout **color** next to their name. It shows when **Printout → Color** is **By person**. **Automatic** gives the person the first of the 10 colors that no one else picked.
- The sheet lists the owner sections in the order you added the owners.
- ✕ removes an owner. You can remove an owner only after you reassign or delete their chores.

## The sheet

The printout has two styles. You choose one on the **Settings** tab, under **Printout**.

| Style | Layout |
|---|---|
| **Cards** (default) | A rounded card for each person, two to a row, then **Shared**, then **No owner** (only when it has chores). The cards in a row end level. **Extra** fills the rest of the page. |
| **Week grid** | One table: a column for each 7 days of the month (1–7, 8–14, …) and an **Any time** column. A box with a date goes in the column of its week. |

- Each person's heading shows their load, including their part of shared chores. The Shared heading shows the total shared time.
- A chore with turns appears in each person's section, with only that person's boxes.
- A week chore gets one box per due date, labelled with the day of the month. Each date belongs to the month that contains it.
  - **With a day**, for example Tuesday: each box falls on that day. A Tuesday on December 1 goes on December's sheet, even when the rest of its week is in November. The Sheet tab shows the day, for example "2 weeks · Tue".
  - **Any day**: each box stands for the week from Monday, and the label is that Monday's date.
- The printout shows the boxes and the chore name. It leaves out how often a chore repeats; the **Sheet** tab still shows that.
- **Light month:** the text grows, up to the Text size limit, and leaves at least 4 Extra lines.
- **Full month:** the text shrinks, down to 8 pt. Past that, **Fit to one page** gives up more (see the options table). If the month still does not fit, a section continues on the next page under "Name (cont.)", and the app shows a warning.
- **Rows:** every row has the same height and ends in the same line, whether it holds a chore or is a write-in. With shaded rows, the shading takes the place of the lines. So the rows of cards side by side line up. Names and boxes centre in each row. A note goes below its name, and a day number below its box.
- **One-page capacity:** for 3 people, Cards holds about 42 chores (90 with 3 cards per row). Week grid holds about 21 (12 in landscape).
- The **Sheet** tab has two views. **Page** shows the printed page itself, drawn from the same layout as the PDF. **List** shows the chores as a list, without the empty sections, which suits a phone screen better.
- In either view, tap a box to check it off. The ✓ shows at once and saves in the background. A reprint shows checked boxes with ✓. The paper sheet works without this.
- Each corner of the printout has a small decoration that changes with the month. The title and headings take the theme's color. The decoration stays in the margin, and it prints as light gray on a black-and-white printer.

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

### Layouts

A layout is a named set of all the printout options. Select one under **Layout**, then change any option. The sheet always prints with the current options.

| Built-in layout | Changes from Cards |
|---|---|
| **Cards** | None. This is the default. |
| **Week grid** | Style: Week grid, shaded rows. |
| **Basic** | No frames or tints, black and white, no decoration, square boxes, 1 write-in line, no times, no "who" line. |
| **Ink saver** | Black and white, no decoration. |
| **Wide week grid** | Week grid, landscape, color by person, shaded rows. |

- After you change an option, the selector shows **Custom (not saved)**.
- **Save as…** keeps the current options under a name of 1 to 30 characters. Your layouts show under **Yours**.
- To change one of your layouts, save it again under the same name. The app asks before it replaces the old one.
- **Delete** removes one of your layouts. The built-in layouts do not change.

### Printout options

The top of the Printout card holds **Style** and **Write-in lines**. The others are under **More options**.

| Option | Values | Notes |
|---|---|---|
| Style | Cards, Week grid | |
| Write-in lines | 0 to 4 (default 2) | Blank lines after each person's chores. A card can get more, so the cards in a row end level. |
| Fit to one page | On (default), Off | When a month would run onto page 2, the printout gives up, in turn: write-in lines, one at a time; the sections of people with no chores; then text below 8 pt, down to 6.5 pt. It stops as soon as the sheet fits. Your options do not change, and the Sheet tab says what it gave up. |
| Orientation | Portrait, Landscape | |
| Cards per row | 1, 2, 3 | Cards only. A card wider than 5 in shows its chores two to a line. In a narrow card, many dates go on a line under the name, and a long name can end in "…". |
| Text size | Small, Normal, Large | The largest size: 0.9×, 1.15×, and 1.35×. |
| Font | Sans, Serif, Condensed | The font for the whole sheet. Condensed fits longer names in narrow cards. |
| Boxes | Rounded, Square, Circle | |
| Color | Theme, By person, Black and white | **By person:** each owner gets the color picked under **Owners**. Shared, No owner, and Extra keep the theme color. **Black and white:** gray title and headings. The decoration keeps its colors. |
| Decoration | Automatic by month, None, or one theme all year | A fixed theme also sets the color. **None** keeps the month's color. |
| Card frames and tinted headings | On, Off | Off: no card borders and no tinted bands. Each heading gets a rule under it. |
| Shade alternate rows | On, Off | Shades every second row, in both styles. The shading then marks the rows in place of the lines under them. In Extra, a thin divider marks off the "who" part. |
| Custom title | Up to 40 characters | A small line above the month, for example "THE GARCIA HOUSE". |
| Daily list | Top, Bottom, Hidden | At the bottom, Extra fills the space above it. |
| Times in headings | On, Off | |
| People with no chores this month | Show, Hide | When shown, they get a card or group with write-in lines. |
| Extra section | On, Off | Full-width rows: a line for the chore, a line for who does it, and a box. |
| "Who" line on Extra rows | On, Off | |

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

- **Export chores** downloads `chore-chart.json` with your owners, daily chores, chores, printout options, saved layouts, and owner colors. It leaves out the printer settings and check-offs.
- **Import chores** replaces your owners, daily chores, and chores with the ones in a file, after you confirm. When the file has printout options and saved layouts, it replaces those too.

Older files import too: fields that a file does not have get their default values. A file without daily chores or printout options leaves your current ones as they are.

## Network access

The app uses the host network, because printer search needs mDNS (Bonjour) on your LAN. Home Assistant shows a lower security rating for this. The app accepts requests only from Home Assistant's ingress, so other devices on the LAN cannot open it. Avahi in the app only searches. It does not announce any names on your LAN.

## Data

The app keeps its data in `/data`: `chores.json`, `owners.json`, `daily.json`, `done.json` (check-offs), `printout.json` (printout options, saved layouts, and owner colors), and `settings.json`. Home Assistant backups include it. If two people edit the same chore at the same time, the last save wins.

New versions of the app read the data of older versions. Each new chore field has a default value (`CHORE_DEFAULTS` in `app/server.py`), and so does each printout option (`PRINTOUT_OPTIONS` in `app/sheet.py`). So you never re-enter chores or layouts after an update.
