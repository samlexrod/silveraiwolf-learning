# SilverAIWolf Learning

![SilverAIWolf Learning](./silveraiwolf-logo.png)

> NOTE: I am in the process of refactoring all tutorials outside of jupyter notebooks unless the use is data science experimentation. Notbooks will always be acompanied by the corresponding tutorial to productionalization.

## Overview
The purpose of this repository is to document my learning journey in the field of Data Science, DevOps, MLOps, Machine Learning, AI, Front-end Development, Backend Development, Software Engineering, and Business Intelligence. 

I will be sharing tutorials, code snippets, and best practices that I have learned over the years. I will be using Python, Typescript, and SQL as the primary programming languages. However, other languages such as Scala and JavaScript may be used in some tutorials to demonstrate related concepts such as front-end development and big data processing.

It is mainly focused in the following areas:
- Data Engineering
    - Data Ingestion
    - Data Processing
    - Data Storage
    - Data Analysis
- Classical Machine Learning
    - Supervised Learning
    - Unsupervised Learning
    - Semi-Supervised Learning
    - Reinforcement Learning
- Neural Networks & Deep Learning
    - Convolutional Neural Networks
    - Recurrent Neural Networks
    - Generative Adversarial Networks
    - Transformers
- Natural Language Processing
    - Text Classification
    - Named Entity Recognition
    - Sentiment Analysis
    - Machine Translation
    - Question Answering
- Computer Vision
    - Object Detection
    - Image Segmentation
    - Image Classification
    - Image Generation
- Time Series Forecasting
    - ARIMA
    - SARIMA
    - SARIMAX
    - LSTM
    - Prophet
- Real-time Data Processing
- Online Model Monitoring
- Model Deployment & Serving
- Asynchronous Programming for Model Serving
    - FastAPI
    - MLflow
- Model Interpretability, Explainability and Fairness
- A/B Testing
- Software Engineering Best Practices for Data Science Projects

## Top 10 Recently Completed Tutorials


## Refactor in Progress
- [ ] [DevOps IAM-ICA Team Setup](https://github.com/samlexrod/silveraiwolf-learning/blob/master/tutorials/devops-and-deployment/aws/security/iam-identity-center-devops-role-setup.md)
- [ ] [IAM Identity Center Admin Setup](https://github.com/samlexrod/silveraiwolf-learning/blob/master/tutorials/devops-and-deployment/aws/security/setup-first-admin-iam-identity-center.md)
- [ ] [KMS IAM-ICA Security Team Setup](https://github.com/samlexrod/silveraiwolf-learning/blob/master/tutorials/devops-and-deployment/aws/security/iam-identity-center-kms-role-setup.md)
- [ ] [FastAPI Websocket Gemma2 Chatbot](https://github.com/samlexrod/silveraiwolf-learning/blob/master/tutorials/backends/fastapi/fastapi-model-serving-with-chat.ipynb)
- [ ] [FastAPI Quickstart](https://github.com/samlexrod/silveraiwolf-learning/blob/master/tutorials/backends/fastapi/fastapi-quickstart.ipynb)
- [ ] [FastAPI Real-time API](https://github.com/samlexrod/silveraiwolf-learning/blob/master/tutorials/backends/fastapi/fastapi-real-time-api.ipynb)

## Work in Progress
- [ ] [Setting up Serverless MSK]
- [ ] FastAPI Pydantic Models
- [ ] MLflow FastAPI Integration
- [ ] FastAPI Websockets Integration
- [ ] FastAPI Model Serving
- [ ] Dockerize FastAPI App
- [ ] Deploy FastAPI with Kubernetes
- [ ] Real-time Streaming with Kafka
- [ ] Real-time Ingestion with Kafka
- [ ] Real-time Analytics with Flink
- [ ] Gradio Quickstart
- [ ] Gradio for NLP Models
- [ ] Gradio for Computer Vision
- [ ] Streamlit Quickstart
- [ ] Streamlit Dashboards
- [ ] Streamlit for ML Apps
- [ ] Dash for Interactive Visualizations
- [ ] Dash Quickstart
- [ ] Panel for Dashboards
- [ ] Panel Quickstart


## MCP Server Setup

### Leverage LangGraph's MCP Server on Cursor

LangGraph's MCP Server offers an excellent starting point for MCP implementation. This straightforward server allows you to test MCP servers while learning about MCP functionality. You can use it as a foundation to create an MCP server for your own documentation. Specifically, SilverAIWolf's MCP docs can be leveraged to enhance the freshness of your context.

Start by testing the SilverAIWolf MCP Server on Terminal:

```bash
uvx --from mcpdoc mcpdoc \\
  --urls "SilverAIWolf:<https://github.com/samlexrod/silveraiwolf-learning/blob/master/mcpdocs/mcp/mcp.txt> SilverAIWolf:<https://github.com/samlexrod/silveraiwolf-learning/blob/master/mcpdocs/mcp/mcp-full.txt>" \\
  --transport sse \\
  --port 8082 \\
  --host localhost

```

Continue by adding the following to your `.cursor/mcp.json` file:

```json
{
  "mcpServers": {
    "langgraph-docs-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "mcpdoc",
        "mcpdoc",
        "--urls",
        "LangGraph:<https://langchain-ai.github.io/langgraph/llms.txt> LangChain:<https://python.langchain.com/llms.txt>",
        "--transport",
        "stdio"
      ]
    },
    "silveraiwolf-learning-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "mcpdoc",
        "mcpdoc",
        "--urls",
        "SilverAIWolf:<https://github.com/samlexrod/silveraiwolf-learning/blob/master/mcpdocs/mcp/mcp.txt> SilverAIWolf:<https://github.com/samlexrod/silveraiwolf-learning/blob/master/mcpdocs/mcp/mcp-full.txt>",
        "--transport",
        "stdio"
      ]
    }
  }
}
```

And then, add the following Cursor rule:

```
for ANY questions about MCP, use the silveraiwolf-learning-mcp server to help answer --
+ call list_doc_sources tool to get the available llms.txt file
+ call fetch_docs tool to read it
+ reflect on the urls in mcp.txt 
+ reflect on the input question 
+ call fetch_docs on any urls relevant to the question
+ use this to answer the question
```

> Now Cursor will use the SilverAIWolf MCP Server to answer your questions related to MCP ensuring that the context is always up to date.