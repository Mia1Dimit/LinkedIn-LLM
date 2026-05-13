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
title: Messages Changelog Events - LinkedIn | Microsoft Learn
canonicalUrl: https://learn.microsoft.com/en-us/linkedin/dma/member-data-portability/shared/changelog-resource-references/messages?view=li-dma-data-portability-2025-11
config_moniker_range: li-dma-data-portability-unversioned || li-dma-data-portability-2024-05 || li-dma-data-portability-2024-08 || li-dma-data-portability-2024-11 || li-dma-data-portability-2025-02 || li-dma-data-portability-2025-05 || li-dma-data-portability-2025-08 || li-dma-data-portability-2025-11
breadcrumb_path: /linkedin/breadcrumb/toc.json
recommendations: false
feedback_system: Standard
feedback_product_url: https://linkedin.zendesk.com/hc/en-us
uhfHeaderId: MSDocsHeader-LinkedIn
description: Resource References for Messages in Changelog Events
author: sidd607
ms.author: li_akvenkat
ms.date: 2026-04-09T00:00:00.0000000Z
ms.topic: article
ms.service: linkedin
ROBOTS: NOINDEX
locale: en-us
document_id: 3739e01d-5f87-2804-035a-a85807481308
document_version_independent_id: 3739e01d-5f87-2804-035a-a85807481308
updated_at: 2026-04-15T04:56:00.0000000Z
original_content_git_url: https://github.com/MicrosoftDocs/linkedin-api-docs/blob/live/linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/messages.md
gitcommit: https://github.com/MicrosoftDocs/linkedin-api-docs/blob/c972782138be7824d3cead54c13f96bcf13819a3/linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/messages.md
git_commit_id: c972782138be7824d3cead54c13f96bcf13819a3
default_moniker: li-dma-data-portability-2025-11
site_name: Docs
depot_name: MSDN.linkedin-api-docs
page_type: conceptual
toc_rel: ../../toc.json
feedback_help_link_type: ''
feedback_help_link_url: ''
word_count: 1146
asset_id: dma/member-data-portability/shared/changelog-resource-references/messages
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
source_path: linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/messages.md
platformId: 7cdda6f8-0f7b-c39f-6f5e-e2d771dc79c0
---

# Messages Changelog Events - LinkedIn | Microsoft Learn

The identity of the `resourceName` is `messages`. This captures all inbound and outbound messages for direct connection, InMail, Recruiter and Sales Navigator of the members. The method available is `CREATE`.

You can determine whether a Messages event is an inbound or outbound message based on the `actor` field of each event. If the event is an outbound one (e.g. member sends a message), the `actor` field will correspond to the member's `personUrn` and equal to the value of the `owner` field. If the event is inbound, then the field will be of another member's `personUrn`.

All message events' `activity` fields will contain `owner`, `author`, and `thread` fields. These fields will help you figure out the identities of the mailbox and more. The `owner` and `author` field will correspond to the sender's mailbox, which can be personal, Recruiter, or Sales Navigator. The `thread` field contains the `membership` array field that has the `identity` of all the participants in the message thread. For more information on the schema, please refer [here](../../../../shared/references/v2/message-schema).

Below are response examples of inbound and outbound Message events:

- Outbound message with attachment from personal mailbox
- Outbound message from Sales Navigator mailbox
- Inbound message to personal mailbox
- Inbound message to Sales Navigator mailbox
- Outbound GIF message from Recruiter mailbox
- Changelog Event when a member edits a sent message
- Changelog Event when a member deletes a sent message

## Contextual Decoration of entities shared on messages

- Sample response of outbound audio message from personal mailbox
- Sample response of outbound video message from personal mailbox
- Sample response of outbound message with member mention sent from personal mailbox

## Sample response of outbound message activity with attachment from personal mailbox

```json
{
  "owner": "urn:li:person:2qXA98-mVk",
  "resourceId": "0-UzY2MDM0NDMwMzU5NDA0OTUzNjFfNTAw",
  "configVersion": 1,
  "method": "CREATE",
  "activity": {
    "owner": "urn:li:person:2qXA98-mVk",
    "createdAt": 1574383506267,
    "author": "urn:li:person:2qXA98-mVk",
    "id": "0-UzY2MDM0NDMwMzU5NDA0OTUzNjFfNTAw",
    "thread": "urn:li:messagingThread:0-NjU5OTczMTMyOTE1ODQzODkxMg==",
    "readAt": 1574383506000,
    "content": {
      "format": "TEXT",
      "fallback": "Hello from personal message",
      "formatVersion": 1,
      "content": {
        "string": "Hello from personal message"
      },
      "attachments": [
          "urn:li:digitalmediaAsset:C5606AQF245TuEXNVXA"
      ]
    },
    "deliveredAt": 1574383506267
  },
  "resourceName": "messages",
  "resourceUri": "/messages/0-UzY2MDM0NDMwMzU5NDA0OTUzNjFfNTAw",
  "actor": "urn:li:person:2qXA98-mVk",
  "activityId": "b000859e-1239-4d77-b3d3-b8c27ee13409",
  "processedAt": 1574383536887,
  "capturedAt": 1574383506487,
    "thread": "urn:li:messagingThread:0-NjU5OTczMTMyOTE1ODQzODkxMg==",Expand commentComment on line L71
    "id": "0-UzY2MDM0NDMwMzU5NDA0OTUzNjFfNTAw",
    "readAt": 1574383506000,
    "content": {
      "format": "TEXT",
      "fallback": "Hello from personal message",
      "formatVersion": 1,
      "content": {
        "string": "Hello from personal message"
      }
    },
  },
  "id": 977493340
}
```

## Sample request of media download

```http
GET https://api.linkedin.com/mediaDownload/C4E06AQGlz2sDB72DQw/messaging-attachmentFile/0?app=4355721&m=AQL6O71XM7RYCwAAAWcuIskYd_5WgTBEDPP1vu9mgwr17pkmTwAJepazDA&e=1543963290&v=beta&t=12345
-H "Authorization: Bearer <redacted access token>"
```

## Sample response of outbound message activity from Sales Navigator mailbox

```json
{
  "owner": "urn:li:person:2qXA98-mVk",
  "resourceId": "0-UzY2MDM0NDI5OTQyNjU4MTI5OTJfMTAwMA==",
  "configVersion": 1,
  "method": "CREATE",
  "activity": {
    "owner": "urn:li:person:2qXA98-mVk",
    "createdAt": 1574383495992,
    "attachments": [],
    "author": "urn:li:salesIdentity:334326",
    "id": "0-UzY2MDM0NDI5OTQyNjU4MTI5OTJfMTAwMA==",
    "thread": "urn:li:messagingThread:0-NjU5OTczMDkxNTAzODAyNzc3Ng==",
    "readAt": 1574383496000,
    "content": {
      "format": "TEXT",
      "fallback": "Hello from Sales Navigator",
      "formatVersion": 1,
      "content": {
        "string": "Hello from Sales Navigator"
      }
    },
    "deliveredAt": 1574383495992
  },
  "resourceName": "messages",
  "resourceUri": "/messages/0-UzY2MDM0NDI5OTQyNjU4MTI5OTJfMTAwMA==",
  "actor": "urn:li:person:2qXA98-mVk",
  "activityId": "6d43fcff-b56e-4e0f-993b-5a398c89fb5d",
  "processedAt": 1574383527451,
  "capturedAt": 1574383496347,
  "id": 977493324
}
```

## Sample response of inbound message activity to personal mailbox

```json
{
  "owner": "urn:li:person:2qXA98-mVk",
  "resourceId": "0-UzY2MDM0NDgxMzA5MzM1MzA2MjRfNTAw",
  "configVersion": 1,
  "method": "CREATE",
  "activity": {
    "owner": "urn:li:person:kAq_1ptj-v",
    "createdAt": 1574384720910,
    "clientExperience": {
      "clientGeneratedToken": "41453ff9-a796-4259-8b80-e4a5da9f8230"
    },
    "author": "urn:li:person:kAq_1ptj-v",
    "id": "0-UzY2MDM0NDgxMzA5MzM1MzA2MjRfNTAw",
    "thread": "urn:li:messagingThread:0-NjU5OTczMTMyOTE1ODQzODkxMg==",
    "readAt": 1574384721000,
    "content": {
      "format": "TEXT",
      "fallback": "Hello back to personal inbox",
      "formatVersion": 1,
      "content": {
        "string": "Hello back to personal inbox"
      }
    },
    "deliveredAt": 1574384720910
  },
  "resourceName": "messages",
  "resourceUri": "/messages/0-UzY2MDM0NDgxMzA5MzM1MzA2MjRfNTAw",
  "actor": "urn:li:person:kAq_1ptj-v",
  "activityId": "1f9e70cc-925f-4738-a336-718832c9db46",
  "processedAt": 1574384751790,
  "capturedAt": 1574384721128,
  "id": 977493572
}
```

## Changelog Event when a member edits a sent message

When a member edits a sent message:

- The value of `method` field would be `UPDATE`.
- The `activity` contains the edited content of the message.
- The `resourceId` would be same as the original message sent / received by the member.

```json
{
    "owner": "urn:li:person:demo-123",
    "resourceId": "2-demoResourceId123==",
    "activity": {
        "createdAt": 1686212246941,
        "attachments": [],
        "author": "urn:li:person:demo-123",
        "thread": "urn:li:messagingThread:2-demoResourceId123==",
        "content": {
            "format": "TEXT",
            "fallback": "This Sent message has been edited",
            "formatVersion": 1
        }
    },
    "method": "UPDATE",
    "configVersion": 4,
    "parentSiblingActivities": [],
    "resourceName": "messages",
    "resourceUri": "/messages/2-demoResourceId123==",
    "actor": "urn:li:person:demo-123",
    "activityId": "bf2c8e04-99fe-4c9c-be16-4b000b9fd387",
    "processedAt": 1686212247420,
    "activityStatus": "SUCCESS",
    "capturedAt": 1686212247039,
    "siblingActivities": [],
    "id": 1823218385
}
```

## Changelog Event when a member deletes a sent message

When a member deletes a sent message:

- The value of `method` field would be `DELETE`.
- The `activity.content` fields would not be present.
- The `resourceId` would be same as the original message sent / received by the member.

```json
{
    "owner": "urn:li:person:demo-user1",
    "resourceId": "2-demoResourceID==",
    "activity": {
        "createdAt": 1686213029706,
        "attachments": [],
        "author": "urn:li:person:demo-user1",
        "thread": "urn:li:messagingThread:2-demoThreadId=="
    },
    "method": "DELETE",
    "configVersion": 4,
    "parentSiblingActivities": [],
    "resourceName": "messages",
    "resourceUri": "/messages/2-demoResourceID==",
    "actor": "urn:li:person:demo-user1",
    "activityId": "194b0d56-5b05-487f-8b84-da6cbe9e5c31",
    "processedAt": 1686213030032,
    "activityStatus": "SUCCESS",
    "capturedAt": 1686213029729,
    "siblingActivities": [],
    "id": 1823218409
}
```

## Sample response of inbound message activity to Sales Navigator mailbox

```json
{
  "owner": "urn:li:person:2qXA98-mVk",
  "resourceId": "0-UzY2MDM3MjAzODc4OTk1OTI3MDRfNTAw",
  "configVersion": 1,
  "method": "CREATE",
  "activity": {
    "owner": "urn:li:person:kAq_1ptj-v",
    "createdAt": 1574449632116,
    "clientExperience": {
      "clientGeneratedToken": "11daeca1-34af-47c2-b22e-d02a947c33a2"
    },
    "author": "urn:li:person:kAq_1ptj-v",
    "id": "0-UzY2MDM3MjAzODc4OTk1OTI3MDRfNTAw",
    "thread": "urn:li:messagingThread:0-NjU5OTczMDkxNTAzODAyNzc3Ng==",
    "readAt": 1574449632000,
    "content": {
      "format": "TEXT",
      "fallback": "Hello back to Sales Navigator inbox",
      "formatVersion": 1,
      "content": {
        "string": "Hello back to Sales Navigator inbox"
      }
    },
    "deliveredAt": 1574449632116
  },
  "resourceName": "messages",
  "resourceUri": "/messages/0-UzY2MDM3MjAzODc4OTk1OTI3MDRfNTAw",
  "actor": "urn:li:person:kAq_1ptj-v",
  "activityId": "c86c3c71-7844-4ed1-b1fc-66deeac14192",
  "processedAt": 1574449662997,
  "capturedAt": 1574449632331,
  "id": 978988628
}
```

## Sample response of outbound GIF message activity from Recruiter mailbox

```json
{
  "owner": "urn:li:person:2qXA98-mVk",
  "resourceId": "0-UzY123456789",
  "configVersion": 1,
  "method": "CREATE",
  "activity": {
    "owner": "urn:li:person:2qXA98-mVk",
    "createdAt": 1580345063392,
    "attachments": [],
    "author": "urn:li:hireMailbox:00000123456789",
    "id": "0-UzY123456789",
    "thread": "urn:li:messagingThread:0-NjA123456789",
    "readAt": 1580345063000,
    "content": {
      "format": "TEXT",
      "fallback": "",
      "formatVersion": 1,
      "content": {
        "string": ""
      }
    },
    "deliveredAt": 1580345063392,
    "extensionContent": {
      "contentRecordMap": {
        "ThirdPartyMedia": {
          "contentRecord": {
            "com.linkedin.messaging.plugin.content.ThirdPartyMedia": {
              "id": "16144203",
              "media": {
                "gif": {
                  "width": 498,
                  "url": "https://snap.licdn.com/tr/images/09db7a56a494eab4477cfc43ce8ae4db/tenor.gif",
                  "height": 373
                },
                "nanogif": {
                  "width": 120,
                  "url": "https://snap.licdn.com/tr/images/70076b56d82a7cf30d364513ea732998/tenor.gif",
                  "height": 90
                },
                "previewgif": {
                  "width": 220,
                  "url": "https://snap.licdn.com/tr/images/f977153e1c03d21380e3fbd50690190c/tenor.gif",
                  "height": 165
                }
              },
              "title": "",
              "type": "TENOR_GIF"
            }
          },
          "key": "ThirdPartyMedia"
        }
      }
    }
  },
  "resourceName": "messages",
  "resourceUri": "/messages/0-UzY123456789",
  "actor": "urn:li:person:2qXA98-mVk",
  "activityId": "0f9bc010-4cff-4aa9-8b34-862e0c6a0634",
  "processedAt": 1580345094317,
  "activityStatus": "SUCCESS",
  "capturedAt": 1580345063639,
  "id": 1106033436
}
```

## Sample response of outbound audio message from personal mailbox

```json
{
    "owner": "urn:li:person:KhoHfOWYNQ",
    "resourceId": "2-MTYyOTE0MDAzODE2M2I0MTgyMS0wMDMmNjI2ZGZkZWEtZGFkZS00N2FkLTk2YmEtMDY5MWEyNmEyOThhXzAxMg==",
    "activity": {
        "owner": "urn:li:person:KhoHfOWYNQ",
        "attachments": [],
        "clientExperience": {...},
        "author": "urn:li:person:KhoHfOWYNQ",
        "thread": "urn:li:messagingThread:2-NjI2ZGZkZWEtZGFkZS00N2FkLTk2YmEtMDY5MWEyNmEyOThhXzAxMg==",
        "readAt": 1629140038306,
        "content": {
            "format": "LITTLE",
            "formatVersion": 1,
            "fallback": "",
            "content": {
                "string": "{audio|urn:li:digitalmediaAsset:C4E20AQGnXq\\_XPHmP3w}"
            }
        },
        "deliveredAt": 1629140038306,
        "createdAt": 1629140038163,
        "contentFilterReasons": [],
        "contentUrns": [
            "urn:li:digitalmediaAsset:C4E20AQGnXq_XPHmP3w"
        ],
        "id": "2-MTYyOTE0MDAzODE2M2I0MTgyMS0wMDMmNjI2ZGZkZWEtZGFkZS00N2FkLTk2YmEtMDY5MWEyNmEyOThhXzAxMg==",
        "$URN": "urn:li:messagingMessage:2-MTYyOTE0MDAzODE2M2I0MTgyMS0wMDMmNjI2ZGZkZWEtZGFkZS00N2FkLTk2YmEtMDY5MWEyNmEyOThhXzAxMg=="
    },
    "method": "CREATE",
    "configVersion": 13,
    "resourceName": "messages",
    "resourceUri": "/messages/2-MTYyOTE0MDAzODE2M2I0MTgyMS0wMDMmNjI2ZGZkZWEtZGFkZS00N2FkLTk2YmEtMDY5MWEyNmEyOThhXzAxMg==",
    "actor": "urn:li:person:KhoHfOWYNQ",
    "activityId": "a93b1b86-708b-4874-b312-cebcc8b52560",
    "processedAt": 1629140038885,
    "activityStatus": "SUCCESS",
    "capturedAt": 1629140038731,
    "siblingActivities": [],
    "id": 1969381378
}
```

## Sample response of outbound video message from personal mailbox

```json
{
    "owner": "urn:li:person:KhoHfOWYNQ",
    "resourceId": "2-MTYyOTE0MDAyMDM4M2IxMDUxMC0wMDMmNjI2ZGZkZWEtZGFkZS00N2FkLTk2YmEtMDY5MWEyNmEyOThhXzAxMg==",
    "activity": {
        "owner": "urn:li:person:KhoHfOWYNQ",
        "attachments": [],
        "author": "urn:li:person:KhoHfOWYNQ",
        "thread": "urn:li:messagingThread:2-NjI2ZGZkZWEtZGFkZS00N2FkLTk2YmEtMDY5MWEyNmEyOThhXzAxMg==",
        "readAt": 1629140020509,
        "content": {
            "format": "LITTLE",
            "formatVersion": 1,
            "fallback": "",
            "content": {
                "string": "{video|urn:li:digitalmediaAsset:C4E23AQEiWpnWqOxC8w}"
            }
        },
        "deliveredAt": 1629140020509,
        "createdAt": 1629140020383,
        "contentFilterReasons": [],
        "contentUrns": [
            "urn:li:digitalmediaAsset:C4E23AQEiWpnWqOxC8w"
        ],
        "messageContexts": [],
        "id": "2-MTYyOTE0MDAyMDM4M2IxMDUxMC0wMDMmNjI2ZGZkZWEtZGFkZS00N2FkLTk2YmEtMDY5MWEyNmEyOThhXzAxMg==",
        "$URN": "urn:li:messagingMessage:2-MTYyOTE0MDAyMDM4M2IxMDUxMC0wMDMmNjI2ZGZkZWEtZGFkZS00N2FkLTk2YmEtMDY5MWEyNmEyOThhXzAxMg=="
    },
    "method": "CREATE",
    "resourceName": "messages",
    "resourceUri": "/messages/2-MTYyOTE0MDAyMDM4M2IxMDUxMC0wMDMmNjI2ZGZkZWEtZGFkZS00N2FkLTk2YmEtMDY5MWEyNmEyOThhXzAxMg==",
    "actor": "urn:li:person:KhoHfOWYNQ",
    "activityId": "8cd045c2-7cdf-4a6e-b629-3b3a413c7fca",
    "processedAt": 1629140020853,
    "activityStatus": "SUCCESS",
    "capturedAt": 1629140020699,
    "id": 1969381370
}
```

## Sample response of outbound message with member mention sent from personal mailbox

```json
{
    "owner": "urn:li:person:KhoHfOWYNQ",
    "resourceId": "2-MTYyOTEzOTk3NjQ4N2I4OTg1OC0wMDMmNjI2ZGZkZWEtZGFkZS00N2FkLTk2YmEtMDY5MWEyNmEyOThhXzAxMg==",
    "activity": {
        "owner": "urn:li:person:KhoHfOWYNQ",
        "author": "urn:li:person:KhoHfOWYNQ",
        "thread": "urn:li:messagingThread:2-NjI2ZGZkZWEtZGFkZS00N2FkLTk2YmEtMDY5MWEyNmEyOThhXzAxMg==",
        "readAt": 1629139976649,
        "content": {
            "format": "LITTLE",
            "formatVersion": 1,
            "fallback": "This is a test @Siddartha Test",
            "content": {
                "string": "This is a test @[Siddartha Test](urn:li:person:A3iH9CIw-n)"
            }
        },
        "deliveredAt": 1629139976649,
        "createdAt": 1629139976487,
        "contentFilterReasons": [],
        "contentUrns": [
            "urn:li:person:A3iH9CIw-n"
        ],
        "messageContexts": [],
        "id": "2-MTYyOTEzOTk3NjQ4N2I4OTg1OC0wMDMmNjI2ZGZkZWEtZGFkZS00N2FkLTk2YmEtMDY5MWEyNmEyOThhXzAxMg==",
        "$URN": "urn:li:messagingMessage:2-MTYyOTEzOTk3NjQ4N2I4OTg1OC0wMDMmNjI2ZGZkZWEtZGFkZS00N2FkLTk2YmEtMDY5MWEyNmEyOThhXzAxMg=="
    },
    "method": "CREATE",
    "resourceName": "messages",
    "resourceUri": "/messages/2-MTYyOTEzOTk3NjQ4N2I4OTg1OC0wMDMmNjI2ZGZkZWEtZGFkZS00N2FkLTk2YmEtMDY5MWEyNmEyOThhXzAxMg==",
    "actor": "urn:li:person:KhoHfOWYNQ",
    "activityId": "663bfb24-492e-4198-9821-6255719a9143",
    "processedAt": 1629139977514,
    "activityStatus": "SUCCESS",
    "capturedAt": 1629139977339,
    "siblingActivities": [],
    "id": 1969381330
}
```