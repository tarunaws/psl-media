# MediaGenAI AWS Reference Architectures

The following diagrams document the AWS-native deployment pattern for every MediaGenAI use case. Each layout adheres to AWS sample architecture conventions: a secured edge (Amazon CloudFront + AWS WAF + Amazon Route 53 + Amazon Cognito), managed integration (Amazon API Gateway + AWS Lambda/AWS Fargate + AWS Step Functions), and workload-specific AI/media services. Icons below are the official AWS architecture icons.

> **Icon legend**: Every service reference embeds the corresponding AWS icon (48 px) hosted from the official AWS Architecture Icons library so you can copy these sections directly into architecture diagrams or Solutions Constructs.

---

## Shared Edge & Control Plane

| Layer | AWS Service | Purpose |
| --- | --- | --- |
| Edge | ![CloudFront](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Networking-Content-Delivery/Arch_Amazon-CloudFront_48.svg) **Amazon CloudFront** + ![WAF](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Security-Identity-Compliance/Arch_AWS-WAF_48.svg) **AWS WAF** | CDN + security perimeter for SPA assets and signed URLs |
| DNS/Auth | ![Route53](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Networking-Content-Delivery/Arch_Amazon-Route-53_48.svg) **Amazon Route 53**, ![Cognito](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Security-Identity-Compliance/Arch_Amazon-Cognito_48.svg) **Amazon Cognito** | Custom domain routing + user auth (Cognito Hosted UI / JWT) |
| API | ![APIGW](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Application-Integration/Arch_Amazon-API-Gateway_48.svg) **Amazon API Gateway** | Single entry point for SPA → microservices |
| Compute | ![Lambda](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Compute/Arch_AWS-Lambda_48.svg) **AWS Lambda** / ![Fargate](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Compute/Arch_AWS-Fargate_48.svg) **AWS Fargate** | Stateless adapters that call AI/media backends |
| Orchestration | ![StepFunctions](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Application-Integration/Arch_AWS-Step-Functions_48.svg) **AWS Step Functions** | Long-running workflows with human-readable state machines |
| Observability | ![CloudWatch](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Management-Governance/Arch_Amazon-CloudWatch_48.svg) **Amazon CloudWatch** | Logs + metrics + synthetic canaries |

All individual use cases plug into this shared edge and then branch into workload-specific data planes below.

---

## 1. Movie Script Generation

### Data Flow
1. Writers submit briefs via SPA → API Gateway.
2. Lambda validates payload, stores metadata in DynamoDB, and launches a Step Functions workflow.
3. Workflow orchestrates prompt chaining against Amazon Bedrock (Claude / Llama) via guarded templates stored in AWS AppConfig.
4. Generated script is stored in Amazon S3; metadata and tokens recorded in DynamoDB + CloudWatch Logs.
5. Optional PDF rendering is done in AWS Lambda (container image) and delivered back through CloudFront signed URLs.

### AWS Components
| Tier | AWS Service | Role |
| --- | --- | --- |
| Storage | ![S3](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Storage/Arch_Amazon-Simple-Storage-Service_48.svg) **Amazon S3** | Brief uploads + screenplay outputs |
| AI Core | ![Bedrock](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Machine-Learning/Arch_AWS-Bedrock_48.svg) **Amazon Bedrock** | Claude 3 / Llama 3 based long-form generation |
| Config | ![AppConfig](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Management-Governance/Arch_AWS-AppConfig_48.svg) **AWS AppConfig** | Prompt & style-guardrail management |
| Metadata | ![DynamoDB](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Database/Arch_Amazon-DynamoDB_48.svg) **Amazon DynamoDB** | Job states, analytics, download links |

---

## 2. Movie Poster Generation

| Tier | AWS Service | Role |
| --- | --- | --- |
| Storage | ![S3](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Storage/Arch_Amazon-Simple-Storage-Service_48.svg) **Amazon S3** | Brand guardrails, reference art, generated posters |
| Workflow | ![StepFunctions](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Application-Integration/Arch_AWS-Step-Functions_48.svg) **Step Functions** | Branching flow for variations & quality gates |
| Diffusion | ![Bedrock](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Machine-Learning/Arch_AWS-Bedrock_48.svg) **Amazon Bedrock (Titan Image / Stable Diffusion)** *or* ![SageMaker](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Machine-Learning/Arch_Amazon-SageMaker_48.svg) **Amazon SageMaker** | Image generation endpoints |
| Policy | ![DynamoDB](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Database/Arch_Amazon-DynamoDB_48.svg) **DynamoDB** | Guardrail JSON + audit history |
| Content Delivery | ![CloudFront](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Networking-Content-Delivery/Arch_Amazon-CloudFront_48.svg) **CloudFront** | Poster previews & downloads |

---

## 3. AI Subtitling (Subtitle Lab)

| Tier | AWS Service | Role |
| --- | --- | --- |
| Ingest | ![S3](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Storage/Arch_Amazon-Simple-Storage-Service_48.svg) **S3** + ![SQS](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Application-Integration/Arch_Amazon-Simple-Queue-Service_48.svg) **SQS** | Video uploads, job queue |
| Speech | ![Transcribe](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Machine-Learning/Arch_Amazon-Transcribe_48.svg) **Amazon Transcribe** | ASR + diarization |
| Translation | ![Translate](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Machine-Learning/Arch_Amazon-Translate_48.svg) **Amazon Translate** | Multilingual captions |
| Formatting | ![Lambda](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Compute/Arch_AWS-Lambda_48.svg) **Lambda** | SRT/WebVTT formatting, style guides |
| Distribution | ![CloudFront](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Networking-Content-Delivery/Arch_Amazon-CloudFront_48.svg) **CloudFront** | Caption download links |

---

## 4. AI Dubbing (Synthetic Voiceover)

| Tier | AWS Service | Role |
| --- | --- | --- |
| Ingest | ![S3](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Storage/Arch_Amazon-Simple-Storage-Service_48.svg) **S3** | Video + transcript assets |
| Speech Analysis | ![Transcribe](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Machine-Learning/Arch_Amazon-Transcribe_48.svg) **Amazon Transcribe** | Speaker diarization |
| Voice Synthesis | ![Polly](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Machine-Learning/Arch_Amazon-Polly_48.svg) **Amazon Polly** | Neural voice replacement |
| Localization | ![Translate](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Machine-Learning/Arch_Amazon-Translate_48.svg) **Amazon Translate** | Script translation, SSML |
| Video Assembly | ![MediaConvert](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Media-Services/Arch_AWS-Elemental-MediaConvert_48.svg) **AWS Elemental MediaConvert** | Re-mux dubbed audio |
| State | ![StepFunctions](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Application-Integration/Arch_AWS-Step-Functions_48.svg) **Step Functions** | Handles retries + QC hooks |

---

## 5. Scene Summarization

| Tier | AWS Service | Role |
| --- | --- | --- |
| Feature Extraction | ![Rekognition](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Machine-Learning/Arch_Amazon-Rekognition_48.svg) **Amazon Rekognition** | Entities, emotions |
| Speech Capture | ![Transcribe](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Machine-Learning/Arch_Amazon-Transcribe_48.svg) **Transcribe** | Dialogue cues |
| NLP | ![Comprehend](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Machine-Learning/Arch_Amazon-Comprehend_48.svg) **Amazon Comprehend** | Key phrases, sentiment |
| Narrative Gen | ![Bedrock](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Machine-Learning/Arch_AWS-Bedrock_48.svg) **Bedrock** | Recap synthesis |
| Storage | ![S3](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Storage/Arch_Amazon-Simple-Storage-Service_48.svg) **S3** + ![DynamoDB](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Database/Arch_Amazon-DynamoDB_48.svg) **DynamoDB** | Frames + metadata |

---

## 6. Content Moderation

| Tier | AWS Service | Role |
| --- | --- | --- |
| Ingest | ![S3](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Storage/Arch_Amazon-Simple-Storage-Service_48.svg) **S3** | Shots/clips storage |
| Analysis | ![Rekognition](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Machine-Learning/Arch_Amazon-Rekognition_48.svg) **Rekognition (Content Moderation API)** | Unsafe labels, bounding boxes |
| Workflow | ![StepFunctions](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Application-Integration/Arch_AWS-Step-Functions_48.svg) **Step Functions** | Category routing |
| Alerts | ![SNS](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Application-Integration/Arch_Amazon-Simple-Notification-Service_48.svg) **Amazon SNS** | Reviewer notifications |
| Timeline | ![DynamoDB](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Database/Arch_Amazon-DynamoDB_48.svg) **DynamoDB** | Frame-level callouts |

---

## 7. Personalized Trailer

| Tier | AWS Service | Role |
| --- | --- | --- |
| Ingest | ![S3](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Storage/Arch_Amazon-Simple-Storage-Service_48.svg) **S3** | Feature reels + viewer profiles |
| Vision Scoring | ![Rekognition](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Machine-Learning/Arch_Amazon-Rekognition_48.svg) **Rekognition** | Faces, key scenes |
| Personalization | ![Personalize](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Machine-Learning/Arch_Amazon-Personalize_48.svg) **Amazon Personalize** | Rank scenes per viewer taste |
| Assembly | ![MediaConvert](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Media-Services/Arch_AWS-Elemental-MediaConvert_48.svg) **MediaConvert** | Timeline stitching |
| Orchestration | ![StepFunctions](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Application-Integration/Arch_AWS-Step-Functions_48.svg) **Step Functions** | Multi-viewer batching |
| Catalog | ![DynamoDB](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Database/Arch_Amazon-DynamoDB_48.svg) **DynamoDB** | Viewer preferences + trailer manifest |

---

## 8. Semantic Search (Text)

| Tier | AWS Service | Role |
| --- | --- | --- |
| Ingest | ![Textract](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Machine-Learning/Arch_Amazon-Textract_48.svg) **Amazon Textract** | OCR for PDF/DOC |
| Embeddings | ![Bedrock](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Machine-Learning/Arch_AWS-Bedrock_48.svg) **Bedrock Titan Embeddings** | Vector generation |
| Index | ![OpenSearch](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Database/Arch_Amazon-OpenSearch-Service_48.svg) **Amazon OpenSearch Service** | Vector + BM25 search |
| Storage | ![S3](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Storage/Arch_Amazon-Simple-Storage-Service_48.svg) **S3** | Document repository |
| ETL | ![Lambda](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Compute/Arch_AWS-Lambda_48.svg) **Lambda** + ![EventBridge](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Application-Integration/Arch_Amazon-EventBridge_48.svg) **EventBridge** | Trigger ingestion pipelines |

---

## 9. Semantic Search (Video)

| Tier | AWS Service | Role |
| --- | --- | --- |
| Capture | ![KinesisVideo](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Analytics/Arch_Amazon-Kinesis-Video-Streams_48.svg) **Amazon Kinesis Video Streams** / **S3** | Clip ingestion |
| Vision | ![Rekognition](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Machine-Learning/Arch_Amazon-Rekognition_48.svg) **Rekognition Video** | Object/action indexing |
| Speech | ![Transcribe](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Machine-Learning/Arch_Amazon-Transcribe_48.svg) **Transcribe** | Dialogue transcripts |
| Embeddings | ![Bedrock](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Machine-Learning/Arch_AWS-Bedrock_48.svg) **Bedrock** | Multimodal vector store |
| Index | ![OpenSearch](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Database/Arch_Amazon-OpenSearch-Service_48.svg) **OpenSearch** | Semantic + temporal queries |

---

## 10. AI-Powered Video Creation from Image

| Tier | AWS Service | Role |
| --- | --- | --- |
| Prompt API | ![APIGW](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Application-Integration/Arch_Amazon-API-Gateway_48.svg) **API Gateway** + ![Lambda](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Compute/Arch_AWS-Lambda_48.svg) **Lambda** | Receive prompts + reference image uploads, validate quotas |
| Generative Core | ![Bedrock](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Machine-Learning/Arch_AWS-Bedrock_48.svg) **Amazon Bedrock (Nova Reel)** | Image-aware text-to-video inference |
| Post-processing | ![MediaConvert](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Media-Services/Arch_AWS-Elemental-MediaConvert_48.svg) **MediaConvert** | Frame rate, aspect cleanup |
| Storage | ![S3](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Storage/Arch_Amazon-Simple-Storage-Service_48.svg) **S3** (videos + reference images) + ![Glacier](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Storage/Arch_Amazon-S3-Glacier_48.svg) **S3 Glacier** (archive) |
| Catalog | ![DynamoDB](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Database/Arch_Amazon-DynamoDB_48.svg) **DynamoDB** | Run history, reference metadata, signed URLs |

---

## 11. Dynamic Ad Insertion

| Tier | AWS Service | Role |
| --- | --- | --- |
| OTT Delivery | ![MediaPackage](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Media-Services/Arch_AWS-Elemental-MediaPackage_48.svg) **AWS Elemental MediaPackage** | Origin packaging |
| SSAI | ![MediaTailor](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Media-Services/Arch_AWS-Elemental-MediaTailor_48.svg) **AWS Elemental MediaTailor** | Server-side ad stitching |
| Ad Decisioning | ![Lambda](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Compute/Arch_AWS-Lambda_48.svg) **Lambda ADS** + ![DynamoDB](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Database/Arch_Amazon-DynamoDB_48.svg) **DynamoDB** | Viewer profile rules + pacing |
| Analytics | ![KinesisDataStreams](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Analytics/Arch_Amazon-Kinesis-Data-Streams_48.svg) **Amazon Kinesis Data Streams** + ![QuickSight](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Analytics/Arch_Amazon-QuickSight_48.svg) **Amazon QuickSight** | Real-time ad metrics |

---

## 12. AI Based Highlight & Trailer

| Tier | AWS Service | Role |
| --- | --- | --- |
| Storage | ![S3](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Storage/Arch_Amazon-Simple-Storage-Service_48.svg) **S3** | Uploads + highlight outputs |
| Vision Ranking | ![Rekognition](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Machine-Learning/Arch_Amazon-Rekognition_48.svg) **Rekognition Segment Detection** | Shots, events, score moments |
| Orchestration | ![StepFunctions](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Application-Integration/Arch_AWS-Step-Functions_48.svg) **Step Functions** | Separate match vs. generic flows |
| Rendering | ![MediaConvert](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Media-Services/Arch_AWS-Elemental-MediaConvert_48.svg) **MediaConvert** | Clip trimming + stitching |
| Delivery | ![CloudFront](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Networking-Content-Delivery/Arch_Amazon-CloudFront_48.svg) **CloudFront Signed URLs** | Inline playback back to SPA |
| Metadata | ![DynamoDB](https://d1.awsstatic.com/webteam/architecture-icons/Arch_Database/Arch_Amazon-DynamoDB_48.svg) **DynamoDB** | Job state + download URLs |

---

### How to Use This Document
- Import sections into **AWS Architecture Icons (draw.io / Lucidchart)** directly—the icon URLs already point to AWS’ official SVG set.
- Combine the shared edge with any use case slice to produce a complete solution diagram consistent with AWS sample architectures.
- When generating PDFs, keep the legend so reviewers can trace each workload’s compliance posture quickly.
