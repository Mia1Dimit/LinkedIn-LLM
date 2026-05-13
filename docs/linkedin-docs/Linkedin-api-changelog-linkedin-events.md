---
layout: Conceptual
monikers:
- li-dma-data-portability-unversioned
- li-dma-data-portability-2024-05
- li-dma-data-portability-2024-08
- li-dma-data-portability-2024-11
- li-dma-data-portability-2025-02
- li-dma-data-portability-2025-05
- li-dma-data-portability-2025-08
- li-dma-data-portability-2025-11
defaultMoniker: li-dma-data-portability-2025-11
versioningType: Ranged
title: LinkedIn Events Changelog Events - LinkedIn | Microsoft Learn
canonicalUrl: https://learn.microsoft.com/en-us/linkedin/dma/member-data-portability/shared/changelog-resource-references/events?view=li-dma-data-portability-2025-11
config_moniker_range: li-dma-data-portability-unversioned || li-dma-data-portability-2024-05 || li-dma-data-portability-2024-08 || li-dma-data-portability-2024-11 || li-dma-data-portability-2025-02 || li-dma-data-portability-2025-05 || li-dma-data-portability-2025-08 || li-dma-data-portability-2025-11
breadcrumb_path: /linkedin/breadcrumb/toc.json
recommendations: false
feedback_system: Standard
feedback_product_url: https://linkedin.zendesk.com/hc/en-us
uhfHeaderId: MSDocsHeader-LinkedIn
description: Resource References for LinkedIn Events in Changelog Events
author: sidd607
ms.author: li_akvenkat
ms.date: 2026-04-07T00:00:00.0000000Z
ms.topic: article
ms.service: linkedin
ROBOTS: NOINDEX
locale: en-us
document_id: da9cde3d-d077-5253-54ba-1377c1970670
document_version_independent_id: da9cde3d-d077-5253-54ba-1377c1970670
updated_at: 2026-04-15T04:56:00.0000000Z
original_content_git_url: https://github.com/MicrosoftDocs/linkedin-api-docs/blob/live/linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/events.md
gitcommit: https://github.com/MicrosoftDocs/linkedin-api-docs/blob/41ad906405460c3384aa71bc15a38dabd117924b/linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/events.md
git_commit_id: 41ad906405460c3384aa71bc15a38dabd117924b
default_moniker: li-dma-data-portability-2025-11
site_name: Docs
depot_name: MSDN.linkedin-api-docs
page_type: conceptual
toc_rel: ../../toc.json
feedback_help_link_type: ''
feedback_help_link_url: ''
word_count: 536
asset_id: dma/member-data-portability/shared/changelog-resource-references/events
moniker_range_name: 0e594fa083335bf635988665e9387b75
monikers:
- li-dma-data-portability-unversioned
- li-dma-data-portability-2024-05
- li-dma-data-portability-2024-08
- li-dma-data-portability-2024-11
- li-dma-data-portability-2025-02
- li-dma-data-portability-2025-05
- li-dma-data-portability-2025-08
- li-dma-data-portability-2025-11
item_type: Content
source_path: linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/events.md
platformId: 726baef1-2e64-3ca1-7f3c-4bf466a3a0e8
---

# LinkedIn Events Changelog Events - LinkedIn | Microsoft Learn

The identity of the `resourceName` is `events`. Currently, this resource captures all LinkedIn events created by regulated members. This also includes LinkedIn events created by a regulated member on behalf of a Company Page. The methods available are: `CREATE`.

## LinkedIn Event activity schema

| Field | Description | Format |
| --- | --- | --- |
| id | Unique identifier of the event | long |
| name | The name of the event, as input by the user | [MultiLocaleRichText](../../../../shared/references/v2/object-types#multilocalerichtext) |
| vanityName | Vanity name (unique across events) for the event that helps with easy identification. | string |
| description | The description of the event, as input by the user. This field will not be present when event description is not provided by the organizer. | [MultiLocaleRichText](../../../../shared/references/v2/object-types#multilocalerichtext) |
| organizer | Entity responsible for organizing this event - possible URN types: urn:li:person:{personID} (Event created by a regulated member), urn:li:organization:{organizationID} (Event created on behalf of a company page). | string |
| backgroundImage | DigitalMediaAssetUrn of the background image associated with this event | string |
| timeRangeV2.startAt | The start time of the event. | long |
| timeRangeV2.endsAt | The end time of the event. The field will not be present if the organizer hasn't entered an end time during event creation. | long |
| externalUrl | URL external to LinkedIn containing event information. | string |
| settings | Container for various event settings. | EventSettings |
| venueDetails | The additional details about the event venue, on top of the address field, like room name, floor number etc. as input by the user. | [MultiLocaleRichText](../../../../shared/references/v2/object-types#multilocalerichtext) |
| address | The physical address of the event (i.e. where the event is taking place). This field will not be present when address is not provided by the organizer. | Address |
| eventTimezone | The event's timezone in IANA Time Zone database format. | string |
| hashtags | Hashtag urns used to generate event feed, specified by event organizer. | List[string] |
| closed | Flag to indicate if this is a closed event meaning the attendees are required to register before joining the event. | boolean |

#### EventSettings Schema

| Field | Description | Format |
| --- | --- | --- |
| entryCriteria | Entry criteria member needs to satisfy to be able to attend the event. Possible values: <br>- PUBLIC: This event is open to all members.<br>- GATED: A member needs to raise a request to attend the event. | Enum |
| discoveryMode | Mode in which the event can be discovered on LinkedIn. Possible values: <br>- LISTED: Event is discoverable through search/relevance/recommendation channels.<br>- URL\_ONLY: Event can only be discovered via URL. | Enum |
| attendanceMode | Mode in which the attendees can attend an event. Possible values: <br>- IN\_PERSON: The event is an offline only event with physical location associated to it and can only be attended in person.<br>- VIRTUAL: The event is an online only event, which has no physical location associated to it. It can only be attended virtually using streaming URL.<br>- IN\_PERSON\_OR\_VIRTUAL: The event has a physical location to attend in person and also has URL for attending virtually. | Enum |

## Sample activity - LinkedIn event created by a regulated user

```json
{
    "owner": "urn:li:person:<personID>",
    "resourceId": "7022126346663247872",
    "activity": {
        "timeRangeV2": {
            "startsAt": 1674210600000
        },
        "vanityName": "event-vanity-name",
        "settings": {
            "entryCriteria": "PUBLIC",
            "attendanceMode": "VIRTUAL",
            "discoveryMode": "LISTED"
        },
        "externalUrl": "https://companyName.com/eventLink",
        "organizer": "urn:li:person:A3iH9CIw-n",
        "backgroundImage": "urn:li:digitalmediaAsset:D4D1EAQH7emFRT6ZOpw",
        "name": {
            "localized": {
                "en_US": "https://company.name/eventLink"
            },
            "preferredLocale": {
                "country": "US",
                "language": "en"
            }
        },
        "description": {
            "localized": {
                "en_US": {
                    "rawText": "Description Lorem Ipsum"
                }
            },
            "preferredLocale": {
                "country": "US",
                "language": "en"
            }
        },
        "id": <eventID>,
        "eventTimezone": "Asia/Kolkata"
    },
    "method": "CREATE",
    "resourceName": "events",
    "resourceUri": "/events/7022126346663247872",
    "actor": "urn:li:person:<personID>",
    "activityId": "e1f1e63b-2840-4c91-bb44-937c017fa186",
    "activityStatus": "SUCCESS"
}
```