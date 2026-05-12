# LinkedIn Member Snapshot Domains API

## Documentation

For the complete documentation index, visit: [LinkedIn Member Data Portability - Snapshot Domains](https://learn.microsoft.com/en-us/linkedin/dma/member-data-portability/shared/snapshot-domain)

## Available Snapshot Domains

| Domain | Description |
|---|---|
| `ADS_CLICKED` | A list of ads you've clicked on. |
| `MEMBER_FOLLOWING` | A list of people you follow on LinkedIn. |
| `LOGIN` | Shows all the stored account logins for your account. |
| `RICH_MEDIA` | Includes URLs to photos, videos, or documents shared on LinkedIn. |
| `SEARCHES` | A list of your recent searches on LinkedIn. |
| `INFERENCE_TAKEOUT` | Key inferences about you based on your LinkedIn profile and activity. |
| `ALL_COMMENTS` | Comments you've made, excluding those on posts in Groups. |
| `CONTACTS` | Contacts imported on LinkedIn. |
| `EVENTS` | Events you've attended, declined after being invited to, or requested to attend. |
| `RECEIPTS` | Details of purchases associated with the member's LinkedIn account. |
| `AD_TARGETING` | Contains information used by LinkedIn to determine which ads to show you. |
| `REGISTRATION` | The date the member joined LinkedIn. |
| `REVIEWS` | Ratings and reviews provided by the member, including those for products, service providers, and LinkedIn Learning. |
| `ARTICLES` | Articles authored by the member. |
| `PATENTS` | Information about any patents listed on the member's LinkedIn profile. |
| `GROUPS` | LinkedIn groups that the member is a part of. |
| `COMPANY_FOLLOWS` | A list of the entities (e.g., companies) that the member follows on LinkedIn. |
| `INVITATIONS` | Invitations that have been sent and received by the member. |
| `PHONE_NUMBERS` | Phone numbers linked to the member's LinkedIn account. |
| `CONNECTIONS` | Name, position, company, and connection date of 1st degree connections of the member. |
| `EMAIL_ADDRESSES` | History of email addresses associated with the member's account, past or present. |
| `JOB_POSTINGS` | Jobs that have been posted by the user. |
| `JOB_APPLICATIONS` | Jobs that have been applied to by the user in the past. |
| `JOB_SEEKER_PREFERENCES` | Includes preferred job types, locations, industries, company sizes, dream companies, job titles, and activity level. |
| `LEARNING` | LinkedIn Learning videos that have been watched by the member. |
| `INBOX` | Messages sent and received in the member's inbox. |
| `SAVED_JOBS` | Contains information about jobs saved for future reference. |
| `SAVED_JOB_ALERTS` | The member's job alerts including saved date and job alert URLs. |
| `PROFILE` | The basic biographical information that makes up the member's LinkedIn profile. |
| `SKILLS` | Skills added to the member's profile. |
| `POSITIONS` | Job roles listed on the member's profile, including company names, titles, descriptions, locations, and dates. |
| `EDUCATION` | Schools listed on the member's profile, including dates attended, degrees earned, and activities participated in. |
| `TEST_SCORES` | Test scores listed on the member's profile. |
| `CAUSES_YOU_CARE_ABOUT` | Causes included on the member's profile. |
| `PUBLICATIONS` | Publications listed on the member's profile. |
| `PROJECTS` | Projects listed on the member's profile. |
| `ORGANIZATIONS` | Organizations listed on the member's profile. |
| `LANGUAGES` | Languages listed by the member, along with their level of proficiency. |
| `HONORS` | Honors listed on the member's profile. |
| `COURSES` | Courses listed on the member's profile. |
| `CERTIFICATIONS` | Contains a list of certifications included in the member's profile. |
| `RECOMMENDATIONS` | A list of recommendations received and given by the member. |
| `ENDORSEMENTS` | Contains details of given and received endorsements. |
| `MEMBER_SHARE_INFO` | Contains all shared or re-shared posts, including date, URL, shared comments, and visibility status. |
| `SECURITY_CHALLENGE_PIPE` | Contains challenge event information when a member signs in from an unfamiliar device or has enabled two-step verification. Includes date, IP address, user agent string, country/region, and challenge type. |
| `TRUSTED_GRAPH` | Contains confirmed verification information related to identity, workplace, and educational institutions. May include a workplace email or valid government-issued ID. LinkedIn partners with CLEAR, a third-party verification partner. |
| `MARKETPLACE_ENGAGEMENTS` | Contains the event name, date and time, status, and external URL if the event organizer shared one. |
| `MARKETPLACE_PROVIDERS` | Contains information related to services a member provides on Services Marketplace. |
| `MARKETPLACE_OPPORTUNITIES` | Contains information related to services a member is looking for on Services Marketplace. |
| `ACTOR_SAVE_ITEM` | Contains the saved date and URL of a post, article, or other content. |
| `JOB_APPLICANT_SAVED_ANSWERS` | Contains the member's answer to basic job application questions. |
| `TALENT_QUESTION_SAVED_RESPONSE` | Contains the member's answers to job application questions provided by the job poster. |
| `PROFILE_SUMMARY` | Contains AI-generated profile summary. |
| `ALL_LIKES` | Contains the reaction type a member has made to a post. |
| `ALL_VOTES` | Contains information related to polls members have created and voted on. |
| `RECEIPTS_LBP` | Contains information related to the member's purchases of LinkedIn services. |
| `EASYAPPLY_BLOCKING` | Provides user account records for job applications on third-party application tracking systems. |
| `LEARNING_COACH_AI_TAKEOUT` | Stores past conversations with LinkedIn Learning's chatbot, Learning Coach. |
| `LEARNING_COACH_INBOX` | Stores past conversations with LinkedIn Learning's chatbot, Learning Coach. |
| `LEARNING_ROLEPLAY_INBOX` | Provides insights and feedback from interactive learning and real-world practice scenarios. |
| `VOLUNTEERING_EXPERIENCES` | Contains volunteering experience, including organization name, role, cause, start and end date, and description. |
| `ACCOUNT_HISTORY` | Contains the date and time the member's account status changed within the last year. |
| `INSTANT_REPOSTS` | Contains the repost date, time and link. |
| `IDENTITY_CREDENTIALS_AND_ASSETS` | Contains private identity asset and credential data. |
| `ADS_LAN` | Contains LAN ads engagement information, including date, LinkedIn advertising identifier, corresponding web page or mobile application, and action type. |

## API Examples

### Fetch Company Follows Data

```
GET https://api.linkedin.com/rest/memberSnapshotData?q=criteria&domain=COMPANY_FOLLOWS
```

### Fetch All Likes with Count Limit

```
GET https://api.linkedin.com/rest/memberSnapshotData?q=criteria&domain=ALL_LIKES&count=1000
```
