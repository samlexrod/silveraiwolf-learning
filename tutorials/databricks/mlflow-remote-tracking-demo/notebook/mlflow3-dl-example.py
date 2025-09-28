# Databricks notebook source
# MAGIC %md
# MAGIC # MLflow 3.0 deep learning example
# MAGIC
# MAGIC This simple notebook introduces [MLflow on Databricks](https://docs.databricks.com/aws/en/mlflow) for deep learning use cases.  With simple instrumentation using MLflow, you can track metadata, checkpoints, and metrics during your deep learning training jobs.
# MAGIC
# MAGIC This notebook uses PyTorch to train a simple classification model, which is tracked as an MLflow Run. It stores a model checkpoint every 10 epochs, along with accuracy metrics. Each checkpoint is tracked as an MLflow `LoggedModel`. The best checkpoint is then selected and used for batch inference.

# COMMAND ----------

# MAGIC %pip install mlflow>=3.0 --upgrade torch scikit-learn
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset


# COMMAND ----------

# MAGIC %md
# MAGIC ## Prepare data
# MAGIC
# MAGIC Load the Iris dataset from scikit-learn and split it into train/test sets.
# MAGIC
# MAGIC Create instances of `mlflow.data.Dataset` which wrap pandas DataFrame types.  This helps link metrics to this dataset during training.  See [MLflow Dataset Tracking](https://mlflow.org/docs/latest/ml/dataset/) for more details.

# COMMAND ----------

from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split

import mlflow
import mlflow.pytorch
from mlflow.entities import Dataset

# Helper function to prepare data
def prepare_data(df):
    X = torch.tensor(df.iloc[:, :-1].values, dtype=torch.float32)
    y = torch.tensor(df.iloc[:, -1].values, dtype=torch.long)
    return X, y

# Load Iris dataset and prepare the DataFrame
iris = load_iris()
iris_df = pd.DataFrame(data=iris.data, columns=iris.feature_names)
iris_df['target'] = iris.target.astype(float)

# Split into training and testing datasets
train_df, test_df = train_test_split(iris_df, test_size=0.2, random_state=42)

# Below, we prepare data as mlflow.data.Dataset types.
train_dataset = mlflow.data.from_pandas(train_df, name="train")
X_train, y_train = prepare_data(train_dataset.df)

test_dataset = mlflow.data.from_pandas(test_df, name="test")
X_test, y_test = prepare_data(test_dataset.df)

# COMMAND ----------

# MAGIC %md
# MAGIC * Wrapping pandas DataFrames as `mlflow.data.Dataset` types lets you formally track the exact data used in your ML experiments.
# MAGIC * This enables reproducibility, dataset lineage, and links metrics and models directly to the dataset in MLflow's UI and APIs.
# MAGIC * Especially useful for auditing, collaboration, and model governance in deep learning workflows.

# COMMAND ----------

display(train_df)

# COMMAND ----------

# MAGIC %md
# MAGIC # Model setup
# MAGIC
# MAGIC This notebook uses a PyTorch deep neural network built from scratch for the Iris classification task. The model architecture and training loop are fully defined in the notebook, without using any pre-trained weights or external models.

# COMMAND ----------

# Define a basic PyTorch classifier
class IrisClassifier(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super(IrisClassifier, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        return x

# Define the PyTorch model and move it to the device
input_size = X_train.shape[1]
hidden_size = 16
output_size = len(iris.target_names)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
scripted_model = IrisClassifier(input_size, hidden_size, output_size).to(device)

# Helper function to compute accuracy
def compute_accuracy(model, X, y):
    with torch.no_grad():
        outputs = model(X)
        _, predicted = torch.max(outputs, 1)
        accuracy = (predicted == y).sum().item() / y.size(0)
    return accuracy

# COMMAND ----------

# MAGIC %md
# MAGIC ## Train the model
# MAGIC
# MAGIC Train the model and log checkpoints and metrics using MLflow.  Note that training code above and below is regular PyTorch code, and MLflow is only used for lightweight annotation to ensure logging:
# MAGIC
# MAGIC - `mlflow.start_run` wraps the training code to log all iterations under a single run.
# MAGIC - `mlflow.pytorch.log_model` logs model checkpoints periodically.
# MAGIC - `mlflow.log_metric` logs computed metrics alongside checkpoints.

# COMMAND ----------

# Start a run to represent the training job
with mlflow.start_run():
    # Load the training dataset with MLflow. We will link training metrics to this dataset.
    # train_dataset: Dataset = mlflow.data.from_pandas(train_df, name="train")
    # X_train, y_train = prepare_data(train_dataset.df)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(scripted_model.parameters(), lr=0.01)

    for epoch in range(101):
        X_train, y_train = X_train.to(device), y_train.to(device)
        out = scripted_model(X_train)
        loss = criterion(out, y_train)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        # Obtain input and output examples for MLflow Model signature creation
        with torch.no_grad():
            input_example = X_train[:1]
            output_example = scripted_model(input_example)

        # Log a checkpoint with metrics every 10 epochs
        if epoch % 10 == 0:
            # Each newly created LoggedModel checkpoint is linked with its
            # name, params, and step
            model_info = mlflow.pytorch.log_model(
                pytorch_model=scripted_model,
                name=f"torch-iris-{epoch}",
                params={
                    "n_layers": 3,
                    "activation": "ReLU",
                    "criterion": "CrossEntropyLoss",
                    "optimizer": "Adam"
                },
                step=epoch,
                signature=mlflow.models.infer_signature(
                    model_input=input_example.cpu().numpy(),
                    model_output=output_example.cpu().numpy(),
                ),
                input_example=X_train.cpu().numpy(),
            )
            # Log metric on training dataset at step and link to LoggedModel
            mlflow.log_metric(
                key="accuracy",
                value=compute_accuracy(scripted_model, X_train, y_train),
                step=epoch,
                model_id=model_info.model_id,
                dataset=train_dataset
            )


# COMMAND ----------

# MAGIC %md
# MAGIC ## Identify the best checkpoint
# MAGIC
# MAGIC This example produced one MLflow Run (`training_run`) and 11 MLflow Logged Models, one for each checkpoint (at steps 0, 10, …, 100). Using [MLflow’s UI or search API](https://docs.databricks.com/aws/en/mlflow/runs), you can get the checkpoints and rank them by their accuracy.

# COMMAND ----------

ranked_checkpoints = mlflow.search_logged_models(
  output_format="list",
  order_by=[{"field_name": "metrics.accuracy", "ascending": False}]
)

best_checkpoint: mlflow.entities.LoggedModel = ranked_checkpoints[0]
print(best_checkpoint.metrics[0])

# COMMAND ----------

worst_checkpoint: mlflow.entities.LoggedModel = ranked_checkpoints[-1]
print(worst_checkpoint.metrics)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Register the best model
# MAGIC
# MAGIC After selecting the best checkpoint model, register it to the [MLflow model registry](https://docs.databricks.com/aws/en/machine-learning/manage-model-lifecycle). In Databricks, the model registry is integrated with [Unity Catalog](https://docs.databricks.com/aws/en/data-governance/unity-catalog), with unified governance, allowing you to see the model and its metadata on the model version page in Catalog Explorer.

# COMMAND ----------

# You must have `USE CATALOG` privileges on the catalog, and you must have `USE SCHEMA` privileges on the schema.
# If necessary, change the catalog and schema name here.

CATALOG = "main"
SCHEMA = "default"
MODEL = "dl_model"
MODEL_NAME = f"{CATALOG}.{SCHEMA}.{MODEL}"

uc_model_version = mlflow.register_model(f"models:/{best_checkpoint.model_id}", name=MODEL_NAME)

# COMMAND ----------

uc_model_version.version

# COMMAND ----------

# MAGIC %md Now you can view the model version and all centralized performance data on the model version page in Unity Catalog. You can also get the same information using the API as shown in the following cell.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Perform inference on test data
# MAGIC
# MAGIC Models logged to MLflow can be loaded for both batch inference and real-time serving.  Below, `mlflow.pyfunc.load_model` loads the model for batch inference.

# COMMAND ----------

import mlflow.pyfunc

# Load the model as a PyFuncModel
model = mlflow.pyfunc.load_model(
  model_uri=f"models:/{MODEL_NAME}/{uc_model_version.version}")

# Perform prediction
X_test_np = X_test.numpy()
predictions = model.predict(X_test_np)

# Display predictions.  For this 3-class Iris dataset, you would take the max for each row to identify the predicted class.
display(predictions)

# COMMAND ----------

# MAGIC %md ## Learn more
# MAGIC
# MAGIC For more resources on these topics, see:
# MAGIC
# MAGIC * [MLflow on Databricks](https://docs.databricks.com/aws/en/mlflow)
# MAGIC   * [MLflow Tracking during training](https://docs.databricks.com/aws/en/mlflow/tracking)
# MAGIC   * [MLflow Model Registry and Unity Catalog](https://docs.databricks.com/aws/en/machine-learning/manage-model-lifecycle)
# MAGIC * [Open-source MLflow documentation](https://mlflow.org/docs/latest/ml/)
# MAGIC * Deploying models for [batch inference](https://docs.databricks.com/aws/en/machine-learning/model-inference/) and [real-time serving](https://docs.databricks.com/aws/en/machine-learning/model-serving/custom-models)
