Figma Prompt — Final Navigation & Workflow Standardization (Pre-Frontend Freeze)

This is the final information architecture pass before the Operations frontend freeze.

Do not redesign the application.

Continue using the existing LotSync design language, spacing, typography, colors, components, interaction patterns, and navigation style.

This pass is focused entirely on improving operational consistency across all user roles.

No new backend functionality is required. Use realistic sample data and existing UI components wherever possible.

1. Standardize Vehicle Lookup Across All Roles

Currently the Lot Staff profile contains the only fully functional vehicle lookup page, labeled Vehicles, while other roles use different naming conventions such as Vehicle Lookup.

Standardize this across the application.

Rename every navigation item to:

Vehicles

Reuse the existing Lot Staff Vehicles page as the shared foundation.

Each role should continue seeing role-appropriate actions and information, but navigation should remain consistent.

Examples:

Lot Staff

Full operational actions
Move vehicle
Install tracker
Assign zone
Complete tasks

Lot Manager

Full operational oversight
Team assignments
Inventory health
Vehicle history

Tower Manager

Transportation information
Dealer trade status
Incoming inventory status

Controller

Inventory reconciliation
Audit information
Exception history

The page should feel like one shared feature rather than multiple different implementations.

2. Consolidate Dealer Trades and Deliveries

The current navigation separates:

Dealer Trades
Deliveries

These workflows are nearly identical operationally.

Replace them with a single navigation item:

Transportation

Within this page provide tabs such as:

Dealer Trades

Customer Deliveries

Reuse existing layouts wherever possible.

Dealer Trades should continue handling:

Dealer-to-dealer vehicle movement
Assigned driver
Origin dealership
Destination dealership
Trade lifecycle

Customer Deliveries should handle:

Customer vehicle deliveries
Delivery appointments
Assigned driver
Delivery status
Customer information

Maintain separate datasets while sharing the same overall page structure.

3. Rework Fresh Trades

The current implementation incorrectly represents dealer trades.

Fresh Trades actually represent customer trade-ins that become new dealership inventory.

Redesign this feature around that workflow.

Rename the page:

Trade-Ins

The creation workflow should focus on rapid intake.

Required fields:

VIN

↓

Automatically decode VIN (placeholder)

↓

Auto-populate

Year

Make

Model

Trim

Engine (optional)

Allow manual editing if needed.

Additional fields:

Stock Number

Exterior Color

Mileage (optional)

Purchase Type

Examples:

Customer Trade

Lease Return

Auction Purchase

Manager Notes

Save

Use placeholder decoded data until backend integration.

4. Trade-In Dashboard

Build the dashboard around operational readiness instead of sales.

Each vehicle should display:

Stock #

VIN

Year

Make

Model

Color

Current Status

Assigned Employee (optional)

Date Received

Status examples:

Awaiting Stock Number

Awaiting Keys

Awaiting RecovR

Awaiting Zone Assignment

Ready for Inventory

Completed

Provide:

Search

Filtering

Sorting

Detail panel

Timeline

Activity history

5. Role-Specific Trade-In Views

Reuse the same Trade-In object across departments.

Lot Staff / Lot Manager

Show operational workflow.

Examples:

Assign stock tag

Install RecovR

Assign parking zone

Ready for inventory

Tower Manager

Simplified operational view.

Examples:

Awaiting Stock Number

Awaiting Keys

Ready for Inventory

Sales

Very lightweight view.

Examples:

Trade received

Awaiting inventory

Inventory ready

This should all use the same underlying object with role-based presentation.

6. Update Lot Manager Navigation

Reorganize the sidebar into clearer operational categories.

Replace:

Vehicle Lookup

Fresh Trades

Dealer Trades

Deliveries

With:

Vehicles

Trade-Ins

Transportation

Inventory Sync

Tasks

Team Status

Reports

Settings

Maintain the existing visual style.

7. Apply Navigation Consistency Across Roles

Review every role.

Lot Staff

Lot Manager

Tower Manager

Controller

Ensure:

Shared features use the same names.

Navigation order feels consistent.

Equivalent pages reuse the same components.

Avoid duplicate implementations where possible.

8. Preserve Existing Functionality

Do not remove or redesign:

Dashboard

Tasks

Inventory Sync

Requests

Activity

Settings

Notifications

Command Palette

Login

Vehicle Detail

Only improve navigation structure and workflow organization.

Definition of Done

The application should feel like a single cohesive product.

Vehicle lookup is standardized across every role.

Dealer Trades and Deliveries are unified under Transportation.

Fresh Trades becomes Trade-Ins with a realistic dealership intake workflow.

Trade-In pages support role-specific operational views while sharing one common object model.

Lot Manager navigation reflects real dealership operations instead of separate disconnected pages.

No visual redesigns are introduced.

The frontend remains ready for freeze and backend integration.