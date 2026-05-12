# LinkedIn Member Changelog API

> ## Documentation Index
> Fetch the complete documentation index at: https://learn.microsoft.com/en-us/linkedin/dma/member-data-portability/shared/member-changelog-api


## Endpoint

```
https://api.linkedin.com/rest/memberChangeLogs?q=memberAndApplication&startTime=<START_DATE_ENCODED>&count=<NUMBER_OF_DESIRED_COUNT>
```

## Query Parameters

| Field Name | Required | Description |
|---|---|---|
| `startTime` | No | Represented as an inclusive timestamp in epoch milliseconds. If present, returns all changelog events created after this time. |
| `count` | No | Number of records to return. Recommended: `10`. Maximum: `50`. |

## Member Changelog Events Schema

| Field Name | Description |
|---|---|
| `id` | The unique identifier for the activity event. |
| `capturedAt` | Time the event is captured. |
| `processedAt` | Time the event is processed. |
| `configVersion` | The configuration version used to process this event. Unique to the activity's `resourceName` and `method`. Changes periodically as configurations are updated. Used for debugging purposes. |
| `owner` | The member who owns the record and has retrieval/viewing access to the activity. |
| `actor` | The member who performs the action. |
| `resourceName` | Name of resource being acted upon. |
| `resourceId` | The identifier of the resource. |
| `resourceUri` | URI of the resource being modified. Used for remediation. |
| `method` | The resource method: `CREATE`, `UPDATE`, `PARTIAL_UPDATE`, or `DELETE`. |
| | **Note:** If method is `DELETE`, the `activity` and `processedActivity` fields are empty since the object cannot be captured after deletion. |
| `methodName` | Optional string representing the method's name. Only present in `ACTION` method. |
| `activity` | The original activity data. Used for remediation. |
| `processedActivity` | The decorated original activity containing relevant contextual information (e.g., original share content for comments). Used for archiving. |
| `siblingActivities` | The activities on the same resource level. Returns up to 10 most recent previous activities (e.g., previous comments on a share). |
| `parentSiblingActivities` | The previous activities on the parent resource level. Returns up to 10 most recent previous activities (e.g., previous comments on a parent comment). |
| `activityId` | A unique string identifier of a captured activity. All records from multiple processing attempts share the same `activityId`. |
| `activityStatus` | **NEW!** The status of the event: `SUCCESS`, `FAILURE`, or `SUCCESSFUL_REPLAY`. |

### Activity Status Values

| Status | Description |
|---|---|
| `SUCCESS` | Event is successfully processed on the initial attempt. |
| `FAILURE` | Event has partial or complete processing failure on the initial attempt. The API will not surface multiple FAILURE events of the same activity. |
| `SUCCESSFUL_REPLAY` | Event is successfully reprocessed after one or many attempts. |

## Resource References

- People
- Endorsement
- Recommendation
- Articles
- UGC Posts
- Social Actions
- Organizations
- Invitations
- Messages
- LinkedIn Events