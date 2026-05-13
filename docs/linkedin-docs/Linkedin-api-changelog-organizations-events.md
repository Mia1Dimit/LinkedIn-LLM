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
canonicalUrl: https://learn.microsoft.com/en-us/linkedin/dma/member-data-portability/shared/changelog-resource-references/organizations?view=li-dma-data-portability-2025-11
config_moniker_range: li-dma-data-portability-unversioned || li-dma-data-portability-2024-05 || li-dma-data-portability-2024-08 || li-dma-data-portability-2024-11 || li-dma-data-portability-2025-02 || li-dma-data-portability-2025-05 || li-dma-data-portability-2025-08 || li-dma-data-portability-2025-11
breadcrumb_path: /linkedin/breadcrumb/toc.json
recommendations: false
feedback_system: Standard
feedback_product_url: https://linkedin.zendesk.com/hc/en-us
uhfHeaderId: MSDocsHeader-LinkedIn
description: Resource References for Organizations in Changelog Events
author: sidd607
ms.author: li_akvenkat
ms.date: 2026-04-07T00:00:00.0000000Z
ms.topic: article
ms.service: linkedin
ROBOTS: NOINDEX
locale: en-us
document_id: c3690e68-7fe6-3356-7e9a-9300db8181db
document_version_independent_id: c3690e68-7fe6-3356-7e9a-9300db8181db
updated_at: 2026-04-15T04:56:00.0000000Z
original_content_git_url: https://github.com/MicrosoftDocs/linkedin-api-docs/blob/live/linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/organizations.md
gitcommit: https://github.com/MicrosoftDocs/linkedin-api-docs/blob/c972782138be7824d3cead54c13f96bcf13819a3/linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/organizations.md
git_commit_id: c972782138be7824d3cead54c13f96bcf13819a3
default_moniker: li-dma-data-portability-2025-11
site_name: Docs
depot_name: MSDN.linkedin-api-docs
page_type: conceptual
toc_rel: ../../toc.json
feedback_help_link_type: ''
feedback_help_link_url: ''
word_count: 356
asset_id: dma/member-data-portability/shared/changelog-resource-references/organizations
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
source_path: linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/organizations.md
platformId: 7de3a649-9764-eaab-c5da-faed007915aa
---

# Messages Changelog Events - LinkedIn | Microsoft Learn

The identity of the `resourceName` is `organizations` and `organizationAcls`. Events relating to creation and updating of company pages have `resourceName``organizations`. Events relating to adding or removing admins for a company page have `resourceName``organizationAcls`.

## Organizations Activity - Creating a Company Page

```json
{
    "owner": "urn:li:person:<personID>",
    "resourceId": "82318779",
    "activity": {
        "vanityName": "test-company-Changelog",
        "created": {
            "actor": "urn:li:person:<personID>",
            "time": 1657610981259
        },
        "lastModifiedByAdmin": {
            "actor": "urn:li:person:<personID>",
            "time": 1657610981259
        },
        "defaultLocale": {
            "country": "US",
            "language": "en"
        },
        "organizationType": "NON_PROFIT",
        "entityStatus": "ACTIVE",
        "staffCountRange": "SIZE_1",
        "industries": [
            "urn:li:industry:6"
        ],
        "name": {
            "localized": {
                "en_US": "Test Company Changelog"
            }
        },
        "tagline": {
            "localized": {
                "en_US": "This is a test company"
            }
        },
        "lastModified": {
            "actor": "urn:li:person:<personID>",
            "time": 1657610981259
        },
        "id": 82318779
    },
    "method": "CREATE",
    "configVersion": 1,
    "parentSiblingActivities": [],
    "resourceName": "organizations",
    "resourceUri": "/organizations/82318779",
    "actor": "urn:li:person:<personID>",
    "activityId": "69d7b9cd-5f0c-4138-b8b9-01f5b7e13f34",
    "processedAt": 1657611011610,
    "activityStatus": "SUCCESS",
    "capturedAt": 1657610981505,
    "siblingActivities": [],
    "id": 3331301444
}
```

## Organizations Activity - Updating the description

The `method` for any events relating to updates to the company page is `UPDATE`. Note that the entire updated schema is present in `activity` field.

```json
{
    "owner": "urn:li:person:<personID>",
    "resourceId": "82318779",
    "activity": {
        "vanityName": "test-company-Changelog",
        "created": {
            "actor": "urn:li:person:<personID>",
            "time": 1657610981259
        },
        "associatedHashtags": [],
        "description": {
            "localized": {
                "en_US": "This is an edited description for the company"
            }
        },
        "groups": [],
        "lastModifiedByAdmin": {
            "actor": "urn:li:person:<personID>",
            "time": 1657611245298
        },
        "versionTag": "2479309411",
        "defaultLocale": {
            "country": "US",
            "language": "en"
        },
        "organizationType": "NON_PROFIT",
        "specialties": [],
        "entityStatus": "ACTIVE",
        "staffCountRange": "SIZE_1",
        "industries": [
            "urn:li:industry:6"
        ],
        "name": {
            "localized": {
                "en_US": "Test Company Changelog"
            },
            "preferredLocale": {
                "country": "US",
                "language": "en"
            }
        },
        "tagline": {
            "localized": {
                "en_US": "This is a test company"
            },
            "preferredLocale": {
                "country": "US",
                "language": "en"
            }
        },
        "primaryOrganizationType": "NONE",
        "parentCareersUsed": false,
        "locations": [],
        "lastModified": {
            "actor": "urn:li:person:<personID>",
            "time": 1657611245298
        },
        "revenueRecords": [],
        "id": 82318779
    },
    "method": "UPDATE",
    "configVersion": 1,
    "parentSiblingActivities": [],
    "resourceName": "organizations",
    "resourceUri": "/organizations/82318779",
    "actor": "urn:li:person:<personID>",
    "activityId": "4315b496-d754-4fdc-93db-5c20c84a16fa",
    "processedAt": 1657611275478,
    "activityStatus": "SUCCESS",
    "capturedAt": 1657611245380,
    "siblingActivities": [],
    "id": 3331301460
}
```

## OrganizationsAcls Activity - Adding a new admin

Adding a member as a `Content Administrator` for a company page.

```json
{
    "owner": "urn:li:person:<personID>",
    "resourceId": "organization=urn%3Ali%3Aorganization%3A82318779&role=CONTENT_ADMINISTRATOR&roleAssignee=urn:li:person:<personID>",
    "activity": {
        "roleAssignee": "urn:li:person:<personID>",
        "role": "CONTENT_ADMINISTRATOR",
        "state": "APPROVED",
        "organization": "urn:li:organization:82318779"
    },
    "method": "UPDATE",
    "configVersion": 1,
    "parentSiblingActivities": [],
    "resourceName": "organizationAcls",
    "resourceUri": "/organizationAcls/(organization:urn:li:organization:82318779,role:CONTENT_ADMINISTRATOR,roleAssignee:urn:li:person:<personID>)",
    "actor": "urn:li:person:<personID>",
    "activityId": "d837483e-a63d-43e4-a745-8092631a5d60",
    "processedAt": 1657611164764,
    "activityStatus": "SUCCESS",
    "capturedAt": 1657611134668,
    "siblingActivities": [],
    "id": 3331301452
}
```