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
title: Social Actions Changelog Events - LinkedIn | Microsoft Learn
canonicalUrl: https://learn.microsoft.com/en-us/linkedin/dma/member-data-portability/shared/changelog-resource-references/socialactions?view=li-dma-data-portability-2025-11
config_moniker_range: li-dma-data-portability-unversioned || li-dma-data-portability-2024-05 || li-dma-data-portability-2024-08 || li-dma-data-portability-2024-11 || li-dma-data-portability-2025-02 || li-dma-data-portability-2025-05 || li-dma-data-portability-2025-08 || li-dma-data-portability-2025-11
breadcrumb_path: /linkedin/breadcrumb/toc.json
recommendations: false
feedback_system: Standard
feedback_product_url: https://linkedin.zendesk.com/hc/en-us
uhfHeaderId: MSDocsHeader-LinkedIn
description: Resource References for Social Actions in Changelog Events
author: sidd607
ms.author: li_akvenkat
ms.date: 2024-03-05T00:00:00.0000000Z
ms.topic: article
ms.service: linkedin
ROBOTS: NOINDEX
locale: en-us
document_id: 21ea3160-1f78-0211-d9f7-7d46e9d1ad3f
document_version_independent_id: 21ea3160-1f78-0211-d9f7-7d46e9d1ad3f
updated_at: 2025-08-29T03:45:00.0000000Z
original_content_git_url: https://github.com/MicrosoftDocs/linkedin-api-docs/blob/live/linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/socialActions.md
gitcommit: https://github.com/MicrosoftDocs/linkedin-api-docs/blob/d706d2fef7721b65628388a6e71d4a735acdf57a/linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/socialActions.md
git_commit_id: d706d2fef7721b65628388a6e71d4a735acdf57a
default_moniker: li-dma-data-portability-2025-11
site_name: Docs
depot_name: MSDN.linkedin-api-docs
page_type: conceptual
toc_rel: ../../toc.json
feedback_help_link_type: ''
feedback_help_link_url: ''
word_count: 380
asset_id: dma/member-data-portability/shared/changelog-resource-references/socialactions
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
source_path: linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/socialActions.md
platformId: 0fac458f-590a-1a25-27af-c7822d6572cc
---

# Social Actions Changelog Events - LinkedIn | Microsoft Learn

The identity of the resourceName is `comments` and `likes` . Currently, this resource captures all personal comment and likes the member makes including comment edits.

## Comment activity - comment on a share on an event page

The `activity` will be the same as other Social Action activities. The addition will be in the `ugcPostUrn` decoration on `object` field. Specifically, the `containerEntity` field relating to the [eventUrn](../../../../shared/references/v2/ugc/event).

```json
{
  "owner": "urn:li:person:Ylpq-RobP9",
  "resourceId": "123456789",
  "configVersion": 70,
  "method": "CREATE",
  "activity": {
    "actor": "urn:li:person:Ylpq-RobP9",
    "created": {
      "actor": "urn:li:person:Ylpq-RobP9",
      "time": 1558381270695
    },
    "lastModified": {
      "actor": "urn:li:person:Ylpq-RobP9",
      "time": 1558381270695
    },
    "id": "123456789",
    "message": {
      "attributes": [],
      "text": "What a lovely event!"
    },
    "object": "urn:li:ugcPost:123456789"
  },
  "resourceName": "socialActions/comments",
  "resourceUri": "/socialActions/urn:li:ugcPost:123456789/comments/123456789",
  "actor": "urn:li:person:Ylpq-RobP9",
  "activityId": "5e8a8f37-eff5-4100-97c5-c1cb67e025b4",
  "processedAt": 1558381290429,
  "capturedAt": 1558381270997,
  "id": 841308
}
```

## Comment activity - comment on a share event

The `activity` will be the same format as other Social Action activities. The addition will be in the `ugcPostUrn` decoration on `object` field. Specifically, the `media` field relating to the [eventUrn](../../../../shared/references/v2/ugc/event).

```json
{
  "owner": "urn:li:person:Ylpq-RobP9",
  "resourceId": "123456789",
  "configVersion": 70,
  "method": "CREATE",
  "activity": {
    "actor": "urn:li:person:Ylpq-RobP9",
    "created": {
      "actor": "urn:li:person:Ylpq-RobP9",
      "time": 1558381270695
    },
    "lastModified": {
      "actor": "urn:li:person:Ylpq-RobP9",
      "time": 1558381270695
    },
    "id": "123456789",
    "message": {
      "attributes": [],
      "text": "What a lovely event!"
    },
    "object": "urn:li:ugcPost:123456789"
  },
  "resourceName": "socialActions/comments",
  "resourceUri": "/socialActions/urn:li:ugcPost:123456789/comments/123456789",
  "actor": "urn:li:person:Ylpq-RobP9",
  "activityId": "5e8a8f37-eff5-4100-97c5-c1cb67e025b4",
  "processedAt": 1558381290429,
  "capturedAt": 1558381270997,
  "id": 841308
}
```

## Comment on an article

```json
{
    "activity": {
        "actor": "urn:li:person:KPA1hpZ1yM", 
        "created": {
            "actor": "urn:li:person:KPA1hpZ1yM", 
            "time": 1492112821044
        }, 
        "id": "6258374773714362368", 
        "lastModified": {
            "actor": "urn:li:person:KPA1hpZ1yM", 
            "time": 1492112821044
        }, 
        "likesSummary": {
            "aggregatedTotalLikes": 0, 
            "likedByCurrentUser": false, 
            "selectedLikes": [], 
            "totalLikes": 0
        }, 
        "message": {
            "attributes": [], 
            "text": "This is a comment on a publishing post."
        }, 
        "object": "urn:li:article:7152306652638920611"
    }, 
    "activityId": "12356788990000", 
    "actor": "urn:li:person:KPA1hpZ1yM", 
    "capturedAt": 1492112821184, 
    "configVersion": 8, 
    "id": 1179932, 
    "method": "CREATE", 
    "owner": "urn:li:person:KPA1hpZ1yM", 
    "processedAt": 1492112834618, 
    "resourceId": "6258374773714362368", 
    "resourceName": "socialActions/comments", 
    "resourceUri": "/socialActions/urn:li:article:7152306652638920611/comments/6258374773714362368"
}
```

## Comment edit activity

```json
{

    "activity": {
        "message": {
            "text": "Edited previous comment"
        }
    }, 
    "activityId": "23995cd8-4441-4e33-a724-090dfcde8b2e", 
    "actor": "urn:li:person:Ylpq-RobP9", 
    "capturedAt": 1520274822960, 
    "configVersion": 1, 
    "id": 647971, 
    "method": "PARTIAL_UPDATE", 
    "owner": "urn:li:person:Ylpq-RobP9", 
    "parentSiblingActivities": [], 
    "processedAt": 1520274853352, 
    "resourceId": "6376493321048596480", 
    "resourceName": "socialActions/comments", 
    "resourceUri": "/socialActions/urn:li:activity:6369097974672306176/comments/6376493321048596480", 
    "siblingActivities": []
}
```

## Like activity - like a share

```json
{
  "owner": "urn:li:person:KPA1hpZ1yM",
  "actor": "urn:li:person:KPA1hpZ1yM",
  "resourceId": "urn:li:activity:6257657041524006912",
  "configVersion": 6,
  "method": "CREATE",
  "activity": {
    "actor": "urn:li:person:KPA1hpZ1yM",
    "created": {
      "actor": "urn:li:person:KPA1hpZ1yM",
      "time": 1492112791993
    },
    "lastModified": {
      "actor": "urn:li:person:KPA1hpZ1yM",
      "time": 1492112791993
    },
    "object": "urn:li:activity:6257657041524006912"
  },
  "processedAt": 1492112812255,
  "capturedAt": 1492112792032,
  "resourceName": "socialActions/likes",
  "resourceUri": "/socialActions/urn:li:activity:6257657041524006912/likes/urn:li:person:KPA1hpZ1yM",
  "id": 1179916,
  "activityId": "12356788990000"
}
```