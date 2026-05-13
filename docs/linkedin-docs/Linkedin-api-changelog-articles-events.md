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
title: Articles Changelog Events - LinkedIn | Microsoft Learn
canonicalUrl: https://learn.microsoft.com/en-us/linkedin/dma/member-data-portability/shared/changelog-resource-references/articles?view=li-dma-data-portability-2025-11
config_moniker_range: li-dma-data-portability-unversioned || li-dma-data-portability-2024-05 || li-dma-data-portability-2024-08 || li-dma-data-portability-2024-11 || li-dma-data-portability-2025-02 || li-dma-data-portability-2025-05 || li-dma-data-portability-2025-08 || li-dma-data-portability-2025-11
breadcrumb_path: /linkedin/breadcrumb/toc.json
recommendations: false
feedback_system: Standard
feedback_product_url: https://linkedin.zendesk.com/hc/en-us
uhfHeaderId: MSDocsHeader-LinkedIn
description: Resource References for Articles in Changelog Events
author: sidd607
ms.author: li_akvenkat
ms.date: 2026-04-07T00:00:00.0000000Z
ms.topic: article
ms.service: linkedin
ROBOTS: NOINDEX
locale: en-us
document_id: 608a05a8-492b-c929-ec90-18f468b9a9d9
document_version_independent_id: 608a05a8-492b-c929-ec90-18f468b9a9d9
updated_at: 2026-04-15T04:56:00.0000000Z
original_content_git_url: https://github.com/MicrosoftDocs/linkedin-api-docs/blob/live/linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/articles.md
gitcommit: https://github.com/MicrosoftDocs/linkedin-api-docs/blob/3a03a799cc8f83b9ea65aa9cb8027f23ce0d1771/linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/articles.md
git_commit_id: 3a03a799cc8f83b9ea65aa9cb8027f23ce0d1771
default_moniker: li-dma-data-portability-2025-11
site_name: Docs
depot_name: MSDN.linkedin-api-docs
page_type: conceptual
toc_rel: ../../toc.json
feedback_help_link_type: ''
feedback_help_link_url: ''
word_count: 117
asset_id: dma/member-data-portability/shared/changelog-resource-references/articles
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
source_path: linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/articles.md
platformId: be0e282b-2624-4abd-1782-fb0cafa21658
---

# Articles Changelog Events - LinkedIn | Microsoft Learn

The identity of the `resourceName` is `originalArticles`. Currently, this resource captures all personal published articles. The two methods available are: `ACTION` and `DELETE`. When it's an action, the `methodName` will appear as `createOrUpdateArticle`.

## Article Activity - Publishing a Post

```json
{
    "activity": {
        "article": {
            "authors": [
                {
                    "author": "urn:li:person:KPA1hpZ1yM", 
                    "type": "PRIMARY_AUTHOR"
                }
            ], 
            "content": {
                "com.linkedin.publishing.HtmlContent": {
                    "htmlText": "<p>This is an awesome article!</p>"
                }
            }, 
            "created": 1492111354000, 
            "id": 6258368624109719552, 
            "lastModified": 1492111380000, 
            "state": "PUBLISHED", 
            "title": "Sample Publishing Post", 
            "version": 9
        }, 
        "distOptions": {
            "publishMessage": {
                "text": "Check this article out!"
            }
        }, 
        "submitter": "urn:li:person:KPA1hpZ1yM"
    }, 
    "activityId": "12356788990000", 
    "actor": "urn:li:person:KPA1hpZ1yM", 
    "capturedAt": 1492111403071, 
    "configVersion": 2, 
    "id": 1177820, 
    "method": "ACTION", 
    "methodName": "createOrUpdateArticle", 
    "owner": "urn:li:person:KPA1hpZ1yM", 
    "processedAt": 1492111414624, 
    "resourceId": "6258368624109719552", 
    "resourceName": "originalArticles", 
    "resourceUri": "/originalArticles"
}
```