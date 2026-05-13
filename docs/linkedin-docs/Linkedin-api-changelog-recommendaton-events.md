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
title: Recommendation Changelog Events - LinkedIn | Microsoft Learn
canonicalUrl: https://learn.microsoft.com/en-us/linkedin/dma/member-data-portability/shared/changelog-resource-references/recommendation?view=li-dma-data-portability-2025-11
config_moniker_range: li-dma-data-portability-unversioned || li-dma-data-portability-2024-05 || li-dma-data-portability-2024-08 || li-dma-data-portability-2024-11 || li-dma-data-portability-2025-02 || li-dma-data-portability-2025-05 || li-dma-data-portability-2025-08 || li-dma-data-portability-2025-11
breadcrumb_path: /linkedin/breadcrumb/toc.json
recommendations: false
feedback_system: Standard
feedback_product_url: https://linkedin.zendesk.com/hc/en-us
uhfHeaderId: MSDocsHeader-LinkedIn
description: Resource References for Recommendation in Changelog Events
author: sidd607
ms.author: li_akvenkat
ms.date: 2024-03-05T00:00:00.0000000Z
ms.topic: article
ms.service: linkedin
ROBOTS: NOINDEX
locale: en-us
document_id: 2fede057-704d-85f0-10e2-5830ca494694
document_version_independent_id: 2fede057-704d-85f0-10e2-5830ca494694
updated_at: 2025-08-29T03:45:00.0000000Z
original_content_git_url: https://github.com/MicrosoftDocs/linkedin-api-docs/blob/live/linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/recommendation.md
gitcommit: https://github.com/MicrosoftDocs/linkedin-api-docs/blob/d706d2fef7721b65628388a6e71d4a735acdf57a/linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/recommendation.md
git_commit_id: d706d2fef7721b65628388a6e71d4a735acdf57a
default_moniker: li-dma-data-portability-2025-11
site_name: Docs
depot_name: MSDN.linkedin-api-docs
page_type: conceptual
toc_rel: ../../toc.json
feedback_help_link_type: ''
feedback_help_link_url: ''
word_count: 205
asset_id: dma/member-data-portability/shared/changelog-resource-references/recommendation
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
source_path: linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/recommendation.md
platformId: 0271026e-0d0d-2925-22a2-6c6199d1b256
---

# Recommendation Changelog Events - LinkedIn | Microsoft Learn

The identity of the `resourceName` are `recs` and `recRequests` . Currently, these two resources captures recommendation requests the member asks. After approval, the members will have the option to set the rec to visible on their own profiles. A recommendation is shown on the member's profile page under the Recommendations section. An `recs ACTION` is also available and it involves reordering of the recommendation on the profile page. See examples below:

## RecRequests Activity - Writing a recommendation

```json
{
  "owner": "urn:li:person:Ylpq-RobP9",
  "configVersion": 1,
  "method": "BATCH_CREATE",
  "activity": {
    "requester": "urn:li:person:Ylpq-RobP9",
    "previousRecommendation": "urn:li:recommendation:(urn:li:person:5Lvu9VVW1m,335004)",
    "notification": {
      "subject": "Inspector, can you update this recommendation?",
      "message": "change this \n\n\"John needs this recommendation! He is AMAZING!\""
    },
    "requestee": "urn:li:person:5Lvu9VVW1m",
    "requesteeEntity": "urn:li:position:(urn:li:person:5Lvu9VVW1m,38208463)",
    "requesterEntity": "urn:li:position:(urn:li:person:Ylpq-RobP9,47021965)",
    "relationship": "RECOMMENDER_REPORTED_TO_RECOMMENDEE"
  },
  "resourceName": "recRequests",
  "resourceUri": "/recRequests/urn:li:recommendationRequest:(urn:li:person:Ylpq-RobP9,266824)",
  "actor": "urn:li:person:Ylpq-RobP9",
  "processedAt": 1486517118769,
  "capturedAt": 1486517091202,
  "id": 7963,
  "activityId": "12356788990000"
}
```

## Recs Activity - Displaying the recommendation on profile

```json
{
    "activity": {
        "status": "VISIBLE"
    }, 
    "activityId": "12356788990000", 
    "actor": "urn:li:person:Ylpq-RobP9", 
    "capturedAt": 1489515453144, 
    "configVersion": 3, 
    "id": 10660, 
    "method": "PARTIAL_UPDATE", 
    "owner": "urn:li:person:Ylpq-RobP9", 
    "processedAt": 1489515468590, 
    "resourceName": "recs", 
    "resourceUri": "/recs/urn:li:recommendation:(urn:li:person:5Lvu9VVW1m,335644)"
}
```

## Recs Activity - ACTION reorder of a recommendation

```json
{
    "activity": {
        "moveRecommendation": "urn:li:recommendation:(urn:li:person:5Lvu9VVW1m,335014)", 
        "recommendeeEntity": "urn:li:position:(urn:li:person:Ylpq-RobP9,47050422)"
    }, 
    "activityId": "12356788990000", 
    "actor": "urn:li:person:Ylpq-RobP9", 
    "capturedAt": 1487024072057, 
    "configVersion": 4, 
    "id": 8771, 
    "method": "ACTION", 
    "owner": "urn:li:person:Ylpq-RobP9", 
    "processedAt": 1487024076827, 
    "resourceName": "recs", 
    "resourceUri": "/recs"
}
```