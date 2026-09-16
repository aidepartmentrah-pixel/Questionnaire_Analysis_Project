# Automated Machine Learning Demonstration — Software Requirements

## 1. Project purpose

The application is a small college project intended to demonstrate an end-to-end machine-learning workflow.

It must demonstrate the ability to:

- Upload and inspect a dataset.
- Perform exploratory data analysis.
- Preprocess data.
- Select a machine-learning task.
- Train three relevant models.
- Tune the hyperparameters of every model.
- Compare the trained models.
- Present evaluation metrics and visualizations.
- Export trained models and generated graphs.

The application is a demonstration and is not intended to be a production-scale AutoML platform.

---

## 2. Technology requirements

- The backend shall be developed using **Python and FastAPI**.
- The frontend shall be developed using **TypeScript**.
- The frontend shall communicate with the backend through REST API endpoints.
- The system shall initially run as a local web application.

---

## 3. Supported machine-learning tasks

The application shall support three types of machine-learning behavior:

1. **Regression**
2. **Classification**
3. **Clustering**

> The term “classification” replaces “prediction” because regression and classification are both forms of prediction. Classification is the correct name for predicting categories or labels.

The user shall select one task before configuring and starting training.

---

## 4. Supported models

Each task shall contain exactly three models.

### 4.1 Regression

The regression task shall include:

- Linear Regression
- Random Forest Regressor
- XGBoost Regressor

### 4.2 Classification

The classification task shall include:

- Logistic Regression
- Random Forest Classifier
- XGBoost Classifier

### 4.3 Clustering

The clustering task shall include:

- K-Means
- Agglomerative Clustering
- DBSCAN

These selections give the project a mixture of linear, tree-based, boosting, centroid-based, hierarchical, and density-based algorithms.

---

## 5. CSV dataset upload

The user shall be able to select a CSV file from the computer through a Browse button.

The system shall:

- Accept files in `.csv` format.
- Read the first row as column names.
- Verify that the file contains columns and data records.
- Display a preview of the uploaded data.
- Display the total number of rows and columns.
- Detect numeric and categorical columns.
- Report an understandable error if the file cannot be processed.

Only one dataset shall be active at a time. Uploading another dataset shall replace the current one.

---

## 6. Data profiling and EDA

After uploading the CSV file, the application shall generate an exploratory data analysis report.

The EDA shall contain at least:

- Dataset dimensions
- Column names
- Detected data types
- Descriptive statistics
- Missing-value counts
- Missing-value percentages
- Duplicate-row count
- Unique-value count for every column
- Distributions of numeric features
- Correlation matrix for numeric features
- Frequency distributions for suitable categorical features

After the task and target are selected, the report shall additionally show:

- Target distribution for regression
- Class distribution for classification
- Feature distributions for clustering

The user shall be able to:

- Preview the EDA results inside the interface.
- Download the generated EDA report.

---

## 7. Task configuration

### 7.1 Regression and classification

When the user selects regression or classification, the application shall require the user to select:

- One target column
- The feature columns used for training

All eligible columns except the target shall be selected as features by default.

The user shall be able to exclude columns that should not participate in training, such as:

- IDs
- Names
- Reference numbers
- Free-text columns

### 7.2 Clustering

When the user selects clustering:

- No target column shall be required.
- The user shall select the features used to create the clusters.
- All eligible numeric features shall be selected by default.

---

## 8. Data preprocessing

Before training, the system shall provide a preprocessing stage.

### 8.1 Missing values

For the initial project version:

- Any row containing a missing value in one of the selected columns shall be removed.
- The system shall display how many rows will be removed.
- The system shall display how many usable rows remain.
- Training shall be stopped if insufficient data remains after removing incomplete rows.

This behavior must be shown clearly because dropping every incomplete row can significantly reduce the dataset.

### 8.2 Duplicate records

The system shall detect duplicate rows and allow them to be removed before training.

### 8.3 Numeric feature scaling

The application shall support:

- Min-Max scaling
- Standard scaling
- No scaling

The user shall be able to choose the scaling method.

The system may recommend an appropriate default according to the selected task or model.

### 8.4 Categorical features

For regression and classification:

- Suitable categorical features shall be converted into numeric values using one-hot encoding.
- The fitted encoder shall remain part of the exported preprocessing pipeline.

For clustering:

- The initial version shall operate on selected numeric features.
- Categorical clustering is outside the initial scope.

### 8.5 Data splitting

For regression and classification:

- The processed data shall be divided into training and testing sets.
- The default split shall be 80% training and 20% testing.
- The same split shall be used when comparing all three models.
- A fixed random seed shall be used to make results reproducible.

Clustering shall use the complete processed feature dataset because it does not require supervised training labels.

---

## 9. Training behavior

After configuring the dataset, the user shall choose one of the three task types:

- Regression
- Classification
- Clustering

When training begins:

1. The application shall load the three models belonging to the selected task.
2. Each model shall undergo hyperparameter tuning.
3. Each model shall be trained using its best discovered configuration.
4. Each trained model shall be evaluated.
5. The results of the three models shall be compared.

The user does **not** select only one individual algorithm. Selecting the task causes all three corresponding models to be tuned, trained, and compared.

Therefore, the application trains three models per experiment—not all nine models simultaneously.

---

## 10. Hyperparameter tuning

Hyperparameter tuning is a required feature.

The application shall:

- Define a limited search space for every supported model.
- Test multiple parameter combinations.
- Use cross-validation where applicable.
- record the best parameter combination for every model.
- Train or retain the best-performing configuration.
- Display the selected hyperparameters in the results.

The search spaces shall be deliberately limited so the college demonstration can finish within a reasonable time.

For supervised models, tuning shall use cross-validation on the training data only. The test data shall remain unseen until final evaluation.

For clustering models, tuning shall use suitable internal clustering measurements rather than supervised cross-validation.

---

## 11. Model evaluation

### 11.1 Regression metrics

Regression models shall be evaluated using:

- Mean Absolute Error
- Root Mean Squared Error
- R² score

The primary comparison metric shall be **Root Mean Squared Error**, where a lower value is better.

### 11.2 Classification metrics

Classification models shall be evaluated using:

- Accuracy
- Precision
- Recall
- F1-score
- Confusion matrix

The primary comparison metric shall be **F1-score**, where a higher value is better.

The metrics shall support binary and multiclass classification.

### 11.3 Clustering metrics

Clustering models shall be evaluated using:

- Silhouette score
- Davies–Bouldin score
- Number of generated clusters
- Number of noise points when applicable

The primary comparison metric shall be the **Silhouette score**, where a higher value is generally better.

The interface shall explain that clustering evaluation is different from supervised-model evaluation because the dataset does not provide known correct labels.

---

## 12. Model comparison and recommendation

After training finishes, the application shall display one comparison table containing the results of the three models.

For every model, the system shall show:

- Model name
- Training status
- Training duration
- Best hyperparameters
- Evaluation metrics
- Any warning or failure encountered during training

The system shall highlight the highest-performing model according to the primary metric for the selected task.

The result shall be described as:

> Best-performing model among the tested models.

The application shall not claim that this is the universally best possible algorithm for the dataset.

A failure in one model should not prevent the results of the other models from being displayed.

---

## 13. Visualizations

The application shall generate graphs appropriate to the selected task.

### Regression

- Actual-versus-predicted graph
- Residual graph
- Feature-importance graph when supported

### Classification

- Confusion matrix
- Class-distribution graph
- Feature-importance graph when supported

### Clustering

- Two-dimensional cluster visualization using dimensionality reduction
- Cluster-size distribution
- Noise-point visualization for DBSCAN when applicable

The graphs shall be viewable inside the application.

---

## 14. Export requirements

The user shall be able to export:

- Any successfully trained model
- The best-performing model
- The preprocessing pipeline associated with the model
- Evaluation metrics
- Best hyperparameters
- Generated graphs
- EDA report

The exported model must include the preprocessing operations required to transform future data. The model and its preprocessing pipeline must not be exported as unrelated components.

The exported information shall include enough metadata to identify:

- Task type
- Model type
- Target column, when applicable
- Feature columns
- Preprocessing configuration
- Training date
- Evaluation results

---

## 15. Application workflow

The expected workflow is:

1. The user uploads a CSV dataset.
2. The application validates and previews it.
3. The application generates the initial EDA.
4. The user selects regression, classification, or clustering.
5. The user selects the target and features where applicable.
6. The user configures preprocessing.
7. The application shows the effect of preprocessing.
8. The user starts training.
9. The three applicable models are hyperparameter-tuned.
10. The models are trained and evaluated.
11. The results are compared.
12. The best-performing tested model is highlighted.
13. The user previews and exports models, graphs, metrics, and the EDA report.

---

## 16. Error handling

The application shall provide understandable messages for situations including:

- Invalid or unreadable CSV file
- Empty dataset
- Missing column headers
- Unsupported column types
- Invalid target selection
- Target containing only one class
- Insufficient records after preprocessing
- Too few samples for cross-validation
- Failure of an individual model
- Failure during model export

The interface shall not expose raw backend error traces to the normal user.

---

## 17. Current scope boundaries

The initial application shall not require:

- User accounts
- Authentication
- Permanent experiment history
- Database storage
- Deep-learning models
- Image, audio, or text datasets
- Multiple simultaneous datasets
- Production deployment of exported models
- Automatic generation of a prediction API
- Training all nine models in one operation

# Requirements status
