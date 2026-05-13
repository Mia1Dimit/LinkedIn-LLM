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
title: Invitations Changelog Events - LinkedIn | Microsoft Learn
canonicalUrl: https://learn.microsoft.com/en-us/linkedin/dma/member-data-portability/shared/changelog-resource-references/invitations?view=li-dma-data-portability-2025-11
config_moniker_range: li-dma-data-portability-unversioned || li-dma-data-portability-2024-05 || li-dma-data-portability-2024-08 || li-dma-data-portability-2024-11 || li-dma-data-portability-2025-02 || li-dma-data-portability-2025-05 || li-dma-data-portability-2025-08 || li-dma-data-portability-2025-11
breadcrumb_path: /linkedin/breadcrumb/toc.json
recommendations: false
feedback_system: Standard
feedback_product_url: https://linkedin.zendesk.com/hc/en-us
uhfHeaderId: MSDocsHeader-LinkedIn
description: Resource References for Invitations in Changelog Events
author: sidd607
ms.author: li_akvenkat
ms.date: 2024-03-05T00:00:00.0000000Z
ms.topic: article
ms.service: linkedin
ROBOTS: NOINDEX
locale: en-us
document_id: 67b5a6da-8d29-a4de-7e88-fa917ebf9d96
document_version_independent_id: 67b5a6da-8d29-a4de-7e88-fa917ebf9d96
updated_at: 2026-04-15T04:56:00.0000000Z
original_content_git_url: https://github.com/MicrosoftDocs/linkedin-api-docs/blob/live/linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/invitations.md
gitcommit: https://github.com/MicrosoftDocs/linkedin-api-docs/blob/3a03a799cc8f83b9ea65aa9cb8027f23ce0d1771/linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/invitations.md
git_commit_id: 3a03a799cc8f83b9ea65aa9cb8027f23ce0d1771
default_moniker: li-dma-data-portability-2025-11
site_name: Docs
depot_name: MSDN.linkedin-api-docs
page_type: conceptual
toc_rel: ../../toc.json
feedback_help_link_type: ''
feedback_help_link_url: ''
word_count: 177
asset_id: dma/member-data-portability/shared/changelog-resource-references/invitations
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
source_path: linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/invitations.md
platformId: 28627f40-d0c2-276d-20e8-6d98f63c6512
---

# Invitations Changelog Events - LinkedIn | Microsoft Learn

The identity of the `resourceName` is `invitations`. Currently, this resource captures all invitations acted on behalf of the regulated members. This means an invitation sent by the regulated member will show up whereas an invitation received by the regulated member will not show up unless the member accepts/declines the invitation. The methods available are `ACTION verifyAndCreate` for invitations created or received, `PARTIAL_UPDATE`, `ACTION inviteeClosingInvitation`, `ACTION inviterClosingInvitation`, `ACTION purge`, and `DELETE`.

Note

We do not currently capture address/contact book import.

Refer [here](../../../../shared/integrations/communications/invitations?context=linkedin/dma/member-data-portability/context) for more information on invitations.

## Action verifyAndCreate - Send an Invitation

```json
{
    "owner": "urn:li:person:<inviterID>",
    "resourceId": "7030825461085577216",
    "activity": {
        "invitationV2": {
            "inviter": "urn:li:person:<inviterID>",
            "invitee": "urn:li:person:<inviteeID>",
            "trackingId":"<>"
        }
    },
    "method": "ACTION",
    "configVersion": 7,
    "parentSiblingActivities": [],
    "methodName": "verifyAndCreate",
    "resourceName": "invitations",
    "resourceUri": "/invitations",
    "actor": "urn:li:person:<inviterID>",
    "activityId": "90431a9a-2897-49cc-b0a0-b9a0292dbc04",
    "processedAt": 1676279446917,
    "activityStatus": "SUCCESS",
    "capturedAt": 1676279416795,
    "siblingActivities": [],
    "id": 1757310665
}
```

## Action inviterClosingInvitation - Withdraw an Invitation

```json
{
    "activity": {
        "inviteActionData": [
            {
                "invitationId": "urn:li:invitation:6230172048157614080"
            }
        ], 
        "inviter": "urn:li:person:Ylpq-RobP9", 
        "inviterActionType": "WITHDRAW"
    }, 
    "activityId": "f8b05048-66e4-46bc-8653-f9fe6f9f3719", 
    "actor": "urn:li:person:Ylpq-RobP9", 
    "capturedAt": 1496417998332, 
    "configVersion": 5, 
    "id": 51411, 
    "method": "ACTION", 
    "methodName": "inviterClosingInvitation", 
    "owner": "urn:li:person:Ylpq-RobP9", 
    "processedAt": 1496418019786, 
    "resourceId": "", 
    "resourceName": "invitations", 
    "resourceUri": "/invitations"
}
```