I actually think the Requests screen is where LotSync can differentiate itself the most.

Right now, requests are mixed into Tasks, but conceptually they're different.

Requests = "Someone is asking for something."
Tasks = "Someone has accepted responsibility to do something."

That distinction lines up almost perfectly with the architecture you've spent months building.

A request hasn't become a commitment yet.

My vision

I wouldn't make Requests another copy of the Tasks page.

I'd make it feel like a dispatcher's inbox.

New Requests (5)

[Accept]  [Assign]  [Decline]

---------------------------------------

Dealer Trade Pickup

Jordan Davis
Tower Manager

Pickup vehicle from
Sunrise Honda

Due ASAP

---------------------------------------

Move Vehicle

Ben Wheeler
Sales

Bring A48291
to the showroom

Before 3:00 PM

---------------------------------------

Customer Delivery

Lisa Martinez

Fuel and stage vehicle
for 4:30 delivery

Very communication-oriented.

Three-column layout

Instead of a left filter and giant cards, I'd use something closer to email.

┌────────────┬────────────────────────────┬────────────────────────┐
│ Filters    │ Request List               │ Request Details        │
└────────────┴────────────────────────────┴────────────────────────┘
Left
Inbox (8)

Assigned to Me

Accepted

Completed

Archived

----------------

Tower

Sales

Service

Recon

Controller
Middle
Dealer Trade

Jordan Davis

ASAP

----------------

Move to Showroom

Ben Wheeler

1:30 PM

----------------

Pull Delivery

Sarah Kim

3:00 PM

Just enough information to scan.

Right

Once selected:

Dealer Trade Pickup

Requested by

Jordan Davis

Tower Manager

----------------

Destination

Sunrise Honda

----------------

Vehicles

▼

H72840

G19283

A48291

----------------

Notes

Take dealer plates.

Bring paperwork.

----------------

Accept

Assign

Decline
This fits your backend

Eventually this becomes

Request

↓

Accepted

↓

Task

↓

Completed

↓

Verified

That's beautiful.

Requests don't need execution history.

Tasks do.

Different request types

I'd give each one its own icon.

🚚 Dealer Trade

🚗 Move Vehicle

🎀 Customer Delivery

🏢 Showroom

🛠 Service

⛽ Fuel

🧽 Detail

📍 Locate Vehicle

📦 Miscellaneous

Immediately recognizable.

Request templates

Managers should almost never type everything.

Instead

New Request

○ Move Vehicle

○ Dealer Trade

○ Customer Delivery

○ Fuel

○ Detail

○ Showroom

○ Custom

Then only fill in

Vehicle

Destination

Priority

Notes

Done.

Multi-car requests

This should absolutely carry over.

Dealer Trade

4 Vehicles

▼

H72840

G18291

B39281

P28192

Exactly like Tasks.

Statuses

Requests shouldn't have Task statuses.

I'd use

New

Accepted

Assigned

Converted to Task

Cancelled

Simple.

Search

I'd search by

Stock
VIN
Requester
Department
Destination
Notes
One thing I'd add

I think every request should show why it exists.

Examples:

Requested for

Customer Delivery
Requested for

Dealer Trade
Requested for

Showroom Rotation
Requested for

Sales Appointment

Not just the task itself, but the business reason.

That gives attendants context.

One idea I really like

I'd make requests expire visually.

ASAP

Due in 15 min

Due in 1 hr

Tomorrow

As time approaches,

the card slowly changes

gray

↓

yellow

↓

orange

↓

red

Not flashing.

Just enough that dispatch naturally floats to the top.

Prompt for Figma

Design a dedicated Requests screen for LotSync that feels like a dispatcher inbox rather than another task list.

Requests represent work that has been asked for but has not necessarily become an accepted task yet. They should feel more like communication between departments than work orders.

Use a three-column layout:

Left sidebar for filters (Inbox, Assigned to Me, Accepted, Completed, Archived, plus department filters such as Tower, Sales, Service, Recon, Controller).
Center column containing a compact, highly scannable list of request cards showing requester, request type, priority, due time, and affected vehicle count.
Right detail pane showing the selected request, requester, department, destination, notes, affected vehicles (expandable for multi-vehicle requests), attachments if applicable, and actions.

Support common dealership request types including:

Dealer Trade Pickup
Move Vehicle
Customer Delivery
Showroom Placement
Fuel Vehicle
Detail Vehicle
Service Pull
Locate Vehicle
Custom Request

Multi-vehicle requests should be expandable, displaying all affected vehicles beneath the parent request while keeping the request itself as the primary object.

The primary actions should be Accept, Assign, Convert to Task, and Decline/Cancel depending on request status.

Display request urgency using time-aware labels such as "ASAP", "Due in 30 min", "Today", and "Tomorrow", with increasing visual emphasis as deadlines approach.

Keep the interface clean and operational, emphasizing rapid scanning and communication between dealership departments rather than project management. The screen should complement the existing Tasks page, with Requests representing incoming work and Tasks representing accepted commitments.