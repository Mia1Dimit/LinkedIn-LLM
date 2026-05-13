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
title: UgcPosts Changelog Events - LinkedIn | Microsoft Learn
canonicalUrl: https://learn.microsoft.com/en-us/linkedin/dma/member-data-portability/shared/changelog-resource-references/ugcposts?view=li-dma-data-portability-2025-11
config_moniker_range: li-dma-data-portability-unversioned || li-dma-data-portability-2024-05 || li-dma-data-portability-2024-08 || li-dma-data-portability-2024-11 || li-dma-data-portability-2025-02 || li-dma-data-portability-2025-05 || li-dma-data-portability-2025-08 || li-dma-data-portability-2025-11
breadcrumb_path: /linkedin/breadcrumb/toc.json
recommendations: false
feedback_system: Standard
feedback_product_url: https://linkedin.zendesk.com/hc/en-us
uhfHeaderId: MSDocsHeader-LinkedIn
description: Resource References for UgcPosts in Changelog Events
author: sidd607
ms.author: li_akvenkat
ms.date: 2026-04-07T00:00:00.0000000Z
ms.topic: article
ms.service: linkedin
ROBOTS: NOINDEX
locale: en-us
document_id: 7de4a93b-e5d4-9f92-487b-042e8419bfb4
document_version_independent_id: 7de4a93b-e5d4-9f92-487b-042e8419bfb4
updated_at: 2026-04-15T04:56:00.0000000Z
original_content_git_url: https://github.com/MicrosoftDocs/linkedin-api-docs/blob/live/linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/ugcPosts.md
gitcommit: https://github.com/MicrosoftDocs/linkedin-api-docs/blob/3a03a799cc8f83b9ea65aa9cb8027f23ce0d1771/linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/ugcPosts.md
git_commit_id: 3a03a799cc8f83b9ea65aa9cb8027f23ce0d1771
default_moniker: li-dma-data-portability-2025-11
site_name: Docs
depot_name: MSDN.linkedin-api-docs
page_type: conceptual
toc_rel: ../../toc.json
feedback_help_link_type: ''
feedback_help_link_url: ''
word_count: 687
asset_id: dma/member-data-portability/shared/changelog-resource-references/ugcposts
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
source_path: linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/ugcPosts.md
platformId: 97036bed-321c-9820-4afe-cd78acc87b26
---

# UgcPosts Changelog Events - LinkedIn | Microsoft Learn

The identity of the `resourceName` is `ugcPosts`. This resource captures all user-generated posts. The three methods available are: `CREATE`, `UPDATE`, and `DELETE`.

## UGC Post Activity - Share a Group

```json
{
  "resourceId": "urn:li:ugcPost:6604919668283068416",
  "resourceName": "ugcPosts",
  "resourceUri": "/ugcPosts/urn:li:ugcPost:123456789",
  "configVersion": 71,
  "method": "CREATE",
  "activity": {
    "specificContent": {
      "com.linkedin.ugc.ShareContent": {
        "shareMediaCategory": "URN_REFERENCE",
        "shareFeatures": {
          "hashtags": []
        },
        "shareCommentary": {
          "text": "HELLO!"
        },
        "media": [
          {
            "media": "urn:li:group:12107512",
            "status": "READY"
          }
        ]
      }
    },
    ...
  },
    ...
  },
  ...
}
```

## UGC Post Activity - Share on an Event Page

```json
{
  "owner": "urn:li:person:Ylpq-RobP9",
  "resourceId": "urn:li:ugcPost:123456789",
  "configVersion": 53,
  "method": "CREATE",
  "activity": {
    "lifecycleState": "PUBLISHED",
    "visibility": {
      "com.linkedin.ugc.MemberNetworkVisibility": "CONTAINER"
    },
    "specificContent": {
      "com.linkedin.ugc.ShareContent": {
        "shareMediaCategory": "NONE",
        "shareFeatures": {
          "hashtags": []
        },
        "shareCommentary": {
          "text": "Hello!"
        },
        "media": [],
        "shareCategorization": {}
      }
    },
    "firstPublishedActor": {
      "member": "urn:li:person:Ylpq-RobP9"
    },
    "author": "urn:li:person:Ylpq-RobP9",
    "created": {
      "actor": "urn:li:person:Ylpq-RobP9",
      "time": 1569543293839
    },
    "versionTag": "1",
    "distribution": {
      "feedDistribution": "MAIN_FEED"
    },
    "ugcOrigin": "DESKTOP",
    "containerEntity": "urn:li:event:123456789",
    "id": "urn:li:ugcPost:123456789",
    "lastModified": {
      "time": 1569543293912
    },
    "firstPublishedAt": 1569543293839
  },
  "resourceName": "ugcPosts",
  "resourceUri": "/ugcPosts/urn:li:ugcPost:123456789",
  "actor": "urn:li:person:Ylpq-RobP9",
  "activityId": "1b36d266-cfd6-4d8a-ad4d-0ed6c478f233",
  "processedAt": 1558380117783,
  "capturedAt": 1558380087104,
  "id": 841260
}
```

## UGC Post Activity - Share an Event

```json
{
  "owner": "urn:li:person:Ylpq-RobP9",
  "resourceId": "urn:li:ugcPost:123456789",
  "configVersion": 53,
  "method": "CREATE",
  "activity": {
    "lifecycleState": "PUBLISHED",
    "visibility": {
      "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
    },
    "specificContent": {
      "com.linkedin.ugc.ShareContent": {
        "shareMediaCategory": "URN_REFERENCE",
        "shareFeatures": {
          "hashtags": [
            "urn:li:hashtag:testevent"
          ]
        },
        "shareCommentary": {
          "attributes": [
            {
              "start": 97,
              "length": 16,
              "value": {
                "com.linkedin.common.HashtagAttributedEntity": {
                  "hashtag": "urn:li:hashtag:testevent"
                }
              }
            }
          ],
          "text": "Excited to organize Test Event!\n#testevent\n"
        },
        "media": [
          {
            "media": "urn:li:event:123456789",
            "status": "READY"
          }
        ]
      }
    },
    "author": "urn:li:person:Ylpq-RobP9",
    "created": {
      "actor": "urn:li:person:Ylpq-RobP9",
      "time": 1558380086653
    },
    "ugcOrigin": "DESKTOP",
    "versionTag": "1",
    "id": "urn:li:ugcPost:123456789",
    "lastModified": {
      "time": 1558380086863
    },
    "firstPublishedAt": 1558380086653,
    "distribution": {
      "feedDistribution": "MAIN_FEED"
    }
  },
  "resourceName": "ugcPosts",
  "resourceUri": "/ugcPosts/urn:li:ugcPost:123456789",
  "actor": "urn:li:person:Ylpq-RobP9",
  "activityId": "1b36d266-cfd6-4d8a-ad4d-0ed6c478f233",
  "processedAt": 1558380117783,
  "capturedAt": 1558380087104,
  "id": 841260
}
```

## UGC Post Activity - Publishing a Marketplace Platform Opportunity Share

```json
{
  "owner": "urn:li:person:yrZCpj2ZYQ",
  "resourceId": "urn:li:ugcPost:123456789",
  "configVersion": 36,
  "method": "CREATE",
  "activity": {
    "lifecycleState": "PUBLISHED",
    "visibility": {
      "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
    },
    "specificContent": {
      "com.linkedin.ugc.ShareContent": {
        "shareMediaCategory": "URN_REFERENCE",
        "shareCommentary": {
          "inferredLocale": "en_US",
          "text": "Looking for a plumber!"
        },
        "media": [
          {
            "media": "urn:li:marketplacePlatformOpportunity:(123456789,SERVICE_MARKETPLACE)"
          }
        ],
        "shareCategorization": {}
      }
    },
    "author": "urn:li:person:yrZCpj2ZYQ",
    "id": "urn:li:ugcPost:123456789",
    ...
  },
  "resourceName": "ugcPosts",
  "resourceUri": "/ugcPosts/urn:li:ugcPost:123456789",
  "actor": "urn:li:person:yrZCpj2ZYQ",
  "activityId": "8561f816-517e-49fb-901d-29c589e3b09f",
  "processedAt": 1552071375435,
  "capturedAt": 1552071345264
}
```

## UGC Post Activity - Publishing an Appreciation Share

```json
{
  "owner": "urn:li:person:yrZCpj2ZYQ",
  "resourceId": "urn:li:ugcPost:123456789",
  "configVersion": 36,
  "method": "CREATE",
  "activity": {
    "lifecycleState": "PUBLISHED",
    "visibility": {
      "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
    },
    "specificContent": {
      "com.linkedin.ugc.ShareContent": {
        "shareMediaCategory": "URN_REFERENCE",
        "shareFeatures": {
          "hashtags": [
            "urn:li:hashtag:kudos",
            "urn:li:hashtag:goingaboveandbeyond"
          ]
        },
        "shareCommentary": {
          "attributes": [
            {
              "start": 0,
              "length": 16,
              "value": {
                "com.linkedin.common.MemberAttributedEntity": {
                  "member": "urn:li:person:2SqvgON4PZ"
                }
              }
            },
            {
              "start": 17,
              "length": 6,
              "value": {
                "com.linkedin.common.HashtagAttributedEntity": {
                  "hashtag": "urn:li:hashtag:kudos"
                }
              }
            },
            {
              "start": 75,
              "length": 20,
              "value": {
                "com.linkedin.common.HashtagAttributedEntity": {
                  "hashtag": "urn:li:hashtag:goingaboveandbeyond"
                }
              }
            }
          ],
          "text": "Partners #Kudos The pride you take in your work is truly inspiring #GoingAboveAndBeyond "
        },
        "media": [
          {
            "media": "urn:li:appreciation:123456789",
            "status": "READY"
          }
        ],
        "shareCategorization": {}
      }
    },
    "author": "urn:li:person:yrZCpj2ZYQ",
    "created": {...},
    "ugcOrigin": "DESKTOP",
    "versionTag": "1",
    "id": "urn:li:ugcPost:123456789",
    "lastModified": {...},
    "firstPublishedAt": 1552071344930,
    "distribution": {
      "feedDistribution": "MAIN_FEED"
    }
  },
  "parentSiblingActivities": [],
  "resourceName": "ugcPosts",
  "resourceUri": "/ugcPosts/urn:li:ugcPost:123456789",
  "actor": "urn:li:person:yrZCpj2ZYQ",
  "activityId": "8561f816-517e-49fb-901d-29c589e3b09f",
  "processedAt": 1552071375435,
  "capturedAt": 1552071345264,
  "siblingActivities": [],
  "id": 368573226
}
```

## UGC Post Activity - Publishing a Video Share

```json
{
  "owner": "urn:li:person:123ABC",
  "resourceId": "urn:li:ugcPost:123456789000",
  "configVersion": 3,
  "method": "CREATE",
  "activity": {
    "lifecycleState": "PROCESSING",
    "visibility": {
      "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
    },
    "specificContent": {
      "com.linkedin.ugc.ShareContent": {
        "shareMediaCategory": "VIDEO",
        "shareCommentary": {
          "text": "Funny video"
        },
        "media": [
          {
            "media": "urn:li:digitalmediaAsset:ABCDEFGHIJK123",
            "status": "PROCESSING"
          }
        ],
        "shareCategorization": {}
      }
    },
    "author": "urn:li:person:123ABC",
    "created": {
      "actor": "urn:li:person:123ABC",
      "time": 1506595503212
    },
    "versionTag": "1",
    "id": "urn:li:ugcPost:123456789000",
    "lastModified": {
      "actor": "urn:li:csUser:2",
      "time": 1506595503212
    },
    "contentCertificationRecord": "{\"originCountryCode\":\"ua\",\"modifiedAt\":1506595503212,\"spamRestriction\":{\"classifications\":[],\"contentQualityClassifications\":[],\"systemName\":\"MACHINE_SYNC\",\"lowQuality\":false,\"contentClassificationTrackingId\":\"3F4312E8B381\",\"contentRelevanceClassifications\":[],\"spam\":false}}"
  },
  "parentSiblingActivities": [],
  "resourceName": "ugcPosts",
  "resourceUri": "/ugcPosts/urn:li:ugcPost:123456789000",
  "actor": "urn:li:person:123ABC",
  "processedAt": 1506598504400,
  "capturedAt": 1506595504400,
  "siblingActivities": [],
  "id": 27699900
}
```

## Reshare a Publishing Article

```json
{
  "owner": "urn:li:person:yrZCpj2ZYQ",
  "resourceId": "urn:li:share:123456789",
  "configVersion": 48,
  "method": "CREATE",
  "activity": {
    "lifecycleState": "PUBLISHED",
    "visibility": {
      "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
    },
    "specificContent": {
      "com.linkedin.ugc.ShareContent": {
        "shareMediaCategory": "ARTICLE",
        "shareFeatures": {
          "hashtags": []
        },
        "shareCommentary": {
          "text": "This is a reshare of a publishing article!"
        },
        "media": [
          {
            "media": "urn:li:article:123456789",
            "status": "READY"
          }
        ],
        "shareCategorization": {}
      }
    },
    "author": "urn:li:person:yrZCpj2ZYQ",
    "created": {
      "actor": "urn:li:person:yrZCpj2ZYQ",
      "time": 1554920930600
    },
    "ugcOrigin": "LI_BADGE",
    "versionTag": "1",
    "id": "urn:li:share:123456789",
    "lastModified": {
      "actor": "urn:li:csUser:2",
      "time": 1554920930669
    },
    "firstPublishedAt": 1554920930600,
    "distribution": {
      "feedDistribution": "MAIN_FEED"
    },
    "contentCertificationRecord": "{\"originCountryCode\":\"us\",\"modifiedAt\":1554920930663,\"spamRestriction\":{\"classifications\":[],\"contentQualityClassifications\":[],\"systemName\":\"MACHINE_SYNC\",\"lowQuality\":false,\"contentClassificationTrackingId\":\"6BC84ABA58C2F1E74103D36E427009DB\",\"contentRelevanceClassifications\":[],\"spam\":false}}"
  },
  "parentSiblingActivities": [],
  "resourceName": "ugcPosts",
  "resourceUri": "/ugcPosts/urn:li:share:123456789",
  "actor": "urn:li:person:yrZCpj2ZYQ",
  "activityId": "ff65cc58-69a3-473c-b932-2a91f79f9389",
  "processedAt": 1554920961173,
  "capturedAt": 1554920930859,
  "siblingActivities": [],
  "id": 216111937
}
```