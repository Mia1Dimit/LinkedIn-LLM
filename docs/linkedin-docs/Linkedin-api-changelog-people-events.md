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
title: People Changelog Events - LinkedIn | Microsoft Learn
canonicalUrl: https://learn.microsoft.com/en-us/linkedin/dma/member-data-portability/shared/changelog-resource-references/people?view=li-dma-data-portability-2025-11
config_moniker_range: li-dma-data-portability-unversioned || li-dma-data-portability-2024-05 || li-dma-data-portability-2024-08 || li-dma-data-portability-2024-11 || li-dma-data-portability-2025-02 || li-dma-data-portability-2025-05 || li-dma-data-portability-2025-08 || li-dma-data-portability-2025-11
breadcrumb_path: /linkedin/breadcrumb/toc.json
recommendations: false
feedback_system: Standard
feedback_product_url: https://linkedin.zendesk.com/hc/en-us
uhfHeaderId: MSDocsHeader-LinkedIn
description: Resource References for People in Changelog Events
author: sidd607
ms.author: li_akvenkat
ms.date: 2024-03-05T00:00:00.0000000Z
ms.topic: article
ms.service: linkedin
ROBOTS: NOINDEX
locale: en-us
document_id: d8004134-2b3e-6c92-9a93-1812e9378d64
document_version_independent_id: d8004134-2b3e-6c92-9a93-1812e9378d64
updated_at: 2025-08-29T03:45:00.0000000Z
original_content_git_url: https://github.com/MicrosoftDocs/linkedin-api-docs/blob/live/linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/people.md
gitcommit: https://github.com/MicrosoftDocs/linkedin-api-docs/blob/d706d2fef7721b65628388a6e71d4a735acdf57a/linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/people.md
git_commit_id: d706d2fef7721b65628388a6e71d4a735acdf57a
default_moniker: li-dma-data-portability-2025-11
site_name: Docs
depot_name: MSDN.linkedin-api-docs
page_type: conceptual
toc_rel: ../../toc.json
feedback_help_link_type: ''
feedback_help_link_url: ''
word_count: 386
asset_id: dma/member-data-portability/shared/changelog-resource-references/people
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
source_path: linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/people.md
platformId: 7b152a72-72d2-d2d6-3340-0e664b9e9231
---

# People Changelog Events - LinkedIn | Microsoft Learn

## People Activity - First Name Edit

```json
{
    "activity": {
        "firstName": {
            "localized": {
                "en_US": "Bob"
            }
        }
    }, 
    "activityId": "12356788990000", 
    "actor": "urn:li:person:KPA1hpZ1yM", 
    "capturedAt": 1489510349698, 
    "configVersion": 4, 
    "id": 425180, 
    "method": "PARTIAL_UPDATE", 
    "owner": "urn:li:person:KPA1hpZ1yM", 
    "processedAt": 1489510364841, 
    "resourceName": "people", 
    "resourceUri": "/people/id=KPA1hpZ1yM"
}
```

## People Activity - Add a Language (sub-resource)

```json
{
    "activity": {
        "created": 1489510372136, 
        "name": {
            "localized": {
                "en_US": "Spanish"
            }
        }, 
        "proficiency": "PROFESSIONAL_WORKING"
    }, 
    "activityId": "12356788990000", 
    "actor": "urn:li:person:KPA1hpZ1yM", 
    "capturedAt": 1489510372367, 
    "configVersion": 1, 
    "id": 425196, 
    "method": "CREATE", 
    "owner": "urn:li:person:KPA1hpZ1yM", 
    "processedAt": 1489510376557, 
    "resourceName": "people/languages", 
    "resourceUri": "/people/id=KPA1hpZ1yM/languages/1304204746"
}
```

## Providing Services

The identity of the `resourceName` is `marketplacePlatformProviders`. Currently, this resource appears when the member publishes, edits, or unpublishes the [Providing Service(s)](https://www.linkedin.com/help/linkedin/answer/108387) on their profile. The methods currently available are: `CREATE` and `PARTIAL_UPDATE`. An initial creation of the Providing Service will result in `CREATE` whereas any subsequent edits, including unpublishing and re-publishing, will be a `PARTIAL_UPDATE`. See examples below:

## Providing Service Activity - Create a Providing Service

```json
{
  "owner": "urn:li:person:2qXA98-mVk",
  "resourceId": "(marketplaceType:SERVICE_MARKETPLACE,provider:urn:li:person:2qXA98-mVk)",
  "activity": {
    "preferences": {
      "com.linkedin.marketplaceplatform.servicemarketplace.ServiceProviderPreferences": {
        "servicesPageStatus": "ACTIVE",
        "serviceProviderSkills": {
          "serviceSkills": [
            "urn:li:skill:50342"
          ]
        },
        "servicesDescription": {
          "localized": {
            "en_US": "This is an API service description"
          },
          "preferredLocale": {
            "country": "US",
            "language": "en"
          }
        },
        "optedIntoOpenToExperience": true,
        "optedIntoOpenToExperienceAt": 1615591223446,
        "availableToWorkRemotely": true,
        "profileLocationSelected": true
      }
    },
    "provider": "urn:li:person:2qXA98-mVk",
    "marketplaceType": "SERVICE_MARKETPLACE",
    "status": "ACTIVE"
  },
  "method": "CREATE",
  "configVersion": 3,
  "resourceName": "marketplacePlatformProviders",
  "resourceUri": "/marketplacePlatformProviders/($params:(),marketplaceType:SERVICE_MARKETPLACE,provider:urn:li:person:2qXA98-mVk)",
  "actor": "urn:li:person:2qXA98-mVk",
  "activityId": "e38443c4-9045-4413-aac6-29a3656645a0",
  "processedAt": 1615591254082,
  "activityStatus": "SUCCESS",
  "capturedAt": 1615591223805,
  "id": 2130989972
}
```

## Providing Service Activity - Add a Providing Service

```json
{
  "owner": "urn:li:person:2qXA98-mVk",
  "resourceId": "marketplaceType=SERVICE_MARKETPLACE&provider=urn:li:person:2qXA98-mVk",
  "activity": {
    "preferences": {
      "com.linkedin.marketplaceplatform.servicemarketplace.ServiceProviderPreferences": {
        "servicesDescription": {
          "preferredLocale": {
            "country": "US",
            "language": "en"
          }
        },
        "serviceProviderSkills": {
          "serviceSkills": [
            "urn:li:skill:50342",
            "urn:li:skill:1794"
          ]
        }
      }
    }
  },
  "method": "PARTIAL_UPDATE",
  "configVersion": 3,
  "resourceName": "marketplacePlatformProviders",
  "resourceUri": "/marketplacePlatformProviders/($params:(),marketplaceType:SERVICE_MARKETPLACE,provider:urn:li:person:2qXA98-mVk)",
  "actor": "urn:li:person:2qXA98-mVk",
  "activityId": "12c7e1c8-c989-4e9d-b329-39f329bf2569",
  "processedAt": 1615591401894,
  "activityStatus": "SUCCESS",
  "capturedAt": 1615591371622,
  "id": 2130990044
}
```

## Providing Service Activity - Unpublish Providing Service

```json
{
  "owner": "urn:li:person:2qXA98-mVk",
  "resourceId": "marketplaceType=SERVICE_MARKETPLACE&provider=urn:li:person:2qXA98-mVk",
  "activity": {
    "preferences": {
      "com.linkedin.marketplaceplatform.servicemarketplace.ServiceProviderPreferences": {
        "optedIntoOpenToExperience": false,
        "servicesPageStatus": "UNPUBLISHED"
      }
    }
  },
  "method": "PARTIAL_UPDATE",
  "configVersion": 3,
  "resourceName": "marketplacePlatformProviders",
  "resourceUri": "/marketplacePlatformProviders/($params:(),marketplaceType:SERVICE_MARKETPLACE,provider:urn:li:person:2qXA98-mVk)",
  "actor": "urn:li:person:2qXA98-mVk",
  "activityId": "07df254c-9eb0-44c0-951f-26c94caf47a8",
  "processedAt": 1615591466838,
  "activityStatus": "SUCCESS",
  "capturedAt": 1615591436665,
  "id": 2130990092
}
```

## Providing Service Activity - Publish a Providing Service after unpublish

```json
{
  "owner": "urn:li:person:2qXA98-mVk",
  "resourceId": "marketplaceType=SERVICE_MARKETPLACE&provider=urn:li:person:2qXA98-mVk",
  "activity": {
    "preferences": {
      "com.linkedin.marketplaceplatform.servicemarketplace.ServiceProviderPreferences": {
        "servicesPageStatus": "ACTIVE",
        "serviceProviderSkills": {
          "serviceSkills": [
            "urn:li:skill:38164"
          ]
        },
        "optedIntoOpenToExperience": true
      }
    }
  },
  "method": "PARTIAL_UPDATE",
  "configVersion": 3,
  "resourceName": "marketplacePlatformProviders",
  "resourceUri": "/marketplacePlatformProviders/($params:(),marketplaceType:SERVICE_MARKETPLACE,provider:urn:li:person:2qXA98-mVk)",
  "actor": "urn:li:person:2qXA98-mVk",
  "activityId": "560c7951-d19c-431a-91ff-7b8774b69c1c",
  "processedAt": 1615591542616,
  "activityStatus": "SUCCESS",
  "capturedAt": 1615591512519,
  "id": 2130990148
}
```