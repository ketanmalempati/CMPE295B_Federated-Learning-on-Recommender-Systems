import pandas as pd
import pandas as pd
import json
import gzip
import numpy as np
import random
from surprise import accuracy
from surprise import Dataset
from surprise import Reader
from surprise import SVD,SVDpp, SlopeOne, NMF, NormalPredictor, KNNBaseline, KNNBasic, KNNWithMeans, KNNWithZScore, BaselineOnly, CoClustering

from surprise.model_selection import GridSearchCV
from tqdm import tqdm
import matplotlib.pyplot as plt
from surprise.model_selection.validation import cross_validate

print("Imported all libraries")

books_df = pd.read_csv("C:\\Users\\Teja\Desktop\\gri.csv")
print("Data loaded")
print(books_df.shape)
print(books_df.head())

books_df = books_df.drop(books_df[books_df['is_read'] == 0].index)
books_df = books_df.drop(books_df[books_df['is_reviewed'] == 0].index)
books = books_df.groupby('rating', group_keys=False).apply(lambda x: x.sample(int((len(x)/len(books_df))*750000)))
print(books.shape)

booksdata = books[['user_id', 'book_id', 'rating']]
print(booksdata.head())
print("continuing....")

n=5
best_models = []
best_model_scores = []


### user group 1
reader = Reader(rating_scale=(0, 5))

split_data = np.array_split(booksdata, n)
from surprise.model_selection import train_test_split

for i, part in enumerate(split_data):
    
    """
    SVDpp parameters
    N_factors: The number of factors.
    N_epochs: The number of iterations of the SGD procedure.
    lr_all – The learning rate for all parameters.
    reg_all – The regularization term for all parameters.
    """
    
    svd_params = {
            "n_factors": [10],
        "n_epochs": [10]
        }
    
    data = Dataset.load_from_df(booksdata[['user_id', 'book_id', 'rating']], reader)
    trainset, testset = train_test_split(data, test_size=0.25, random_state=42)

    algo = SVD(n_factors=15,
    n_epochs=50,
    reg_pu=0.06,
    reg_qi=0.06,
    random_state=42,  # Fixed random state for reproducibility
    verbose=True)

    
    algo.fit(trainset)
    best_models.append(algo)
    predictions = algo.test(testset)
    print(accuracy.rmse(predictions))
    
    
def average_attributes(objects):
    # Determine the minimum size across all objects for each attribute
    k = [obj.bi.size for obj in objects]
    min_length_bi = min(k)
    min_length_bu = min(obj.bu.size for obj in objects)
    print(k)
    min_rows_up, min_cols_up = min((obj.pu.shape for obj in objects), key=lambda x: x[0] * x[1])
    min_rows_qi, min_cols_qi = min((obj.qi.shape for obj in objects), key=lambda x: x[0] * x[1])

    # Initialize average arrays
    avg_bi = np.zeros(min_length_bi)
    avg_bu = np.zeros(min_length_bu)
    avg_up = np.zeros((min_rows_up, min_cols_up))
    avg_qi = np.zeros((min_rows_qi, min_cols_qi))
    
    num_objects = len(objects)
    
    # Sum all arrays from each object, resizing as necessary
    for obj in objects:
        avg_bi += np.resize(obj.bi, min_length_bi)
        avg_bu += np.resize(obj.bu, min_length_bu)
        
        avg_up += np.resize(obj.pu, (min_rows_up, min_cols_up))
        avg_qi += np.resize(obj.qi, (min_rows_qi, min_cols_qi))
        
    # Compute the average by dividing each summed array by the number of objects
    avg_bi /= num_objects
    avg_bu /= num_objects
    avg_up /= num_objects
    avg_qi /= num_objects
    
    return avg_bi, avg_bu, avg_up, avg_qi

### fed model
import time

# Start time
start_time = time.time()

# Code block to time
avg_bi, avg_bu, avg_up, avg_qi = average_attributes(best_models)

agg_model = SVD(n_factors=15,
n_epochs=50,
reg_pu=0.06,
reg_qi=0.06,
random_state=42,  # Fixed random state for reproducibility
verbose=True)

agg_model.bi = avg_bi
agg_model.bu = avg_bu
agg_model.pu = avg_up
agg_model.qi = avg_qi
agg_model.trainset = best_models[0].trainset

end_time = time.time()

# Calculate duration
duration = end_time - start_time
print(f"The method took {duration:.2f} seconds to run.")

predictions = agg_model.test(testset)
rmse = accuracy.rmse(predictions)
print(f'RMSE: {rmse}')

from collections import defaultdict

def precision_recall_at_k(predictions, k=10, threshold=3.5):
    '''Return precision and recall at k metrics for each user.'''

    # First map the predictions to each user.
    user_est_true = defaultdict(list)
    for uid, _, true_r, est, _ in predictions:
        user_est_true[uid].append((est, true_r))

    precisions = dict()
    recalls = dict()
    for uid, user_ratings in user_est_true.items():
        # Sort user ratings by estimated value
        user_ratings.sort(key=lambda x: x[0], reverse=True)

        # Number of relevant items
        n_rel = sum((true_r >= threshold) for (_, true_r) in user_ratings)

        # Number of recommended items in top k
        n_rec_k = sum((est >= threshold) for (est, _) in user_ratings[:k])

        # Number of relevant and recommended items in top k
        n_rel_and_rec_k = sum(((true_r >= threshold) and (est >= threshold)) for (est, true_r) in user_ratings[:k])

        # Precision@K: Proportion of recommended items that are relevant
        precisions[uid] = n_rel_and_rec_k / n_rec_k if n_rec_k != 0 else 0

        # Recall@K: Proportion of relevant items that are recommended
        recalls[uid] = n_rel_and_rec_k / n_rel if n_rel != 0 else 0

    return precisions, recalls
def f1_score(precision, recall):
    if precision == 0 and recall == 0:
        return 0
    return 2 * (precision * recall) / (precision + recall)

from surprise import SVD, Dataset, Reader
from surprise.model_selection import train_test_split
from collections import defaultdict



# Compute Precision and Recall at k=10
precisions, recalls = precision_recall_at_k(predictions, k=10, threshold=3.5)

# Average precision and recall over all users
avg_precision = sum(prec for prec in precisions.values()) / len(precisions)
avg_recall = sum(rec for rec in recalls.values()) / len(recalls)

# Compute F1-score
f1 = f1_score(avg_precision, avg_recall)

print(f'RMSE: {rmse}')
print(f'Precision: {avg_precision}')
print(f'Recall: {avg_recall}')
print(f'F1 Score: {f1}')


predictions = [agg_model.predict(uid, iid, r_ui=rating) for (uid, iid, rating) in testset]
# Organize predictions by user
user_ratings = defaultdict(list)
for prediction in predictions:
    uid = prediction.uid
    iid = prediction.iid
    est = prediction.est
    r_ui = prediction.r_ui
    user_ratings[uid].append((iid, r_ui, est))

# Sort by actual and predicted ratings to obtain rankings
user_actual_rankings = {}
user_predicted_rankings = {}
for uid, ratings in user_ratings.items():
    user_actual_rankings[uid] = sorted(ratings, key=lambda x: x[1], reverse=True)
    user_predicted_rankings[uid] = sorted(ratings, key=lambda x: x[2], reverse=True)

# Determine item relevance scores
relevancy = {}
from sklearn.metrics import ndcg_score
ndcg_scores=[]
ndcg_penality = -3
for uid in user_actual_rankings:
    actual_rank = {item: idx for idx, (item, _, _) in enumerate(user_actual_rankings[uid])}
    predicted_rank = {item: idx for idx, (item, _, _) in enumerate(user_predicted_rankings[uid])}
    try:
        ndcg_scores.append(ndcg_score(actual_rank.values(),predicted_rank.values()))
    except:
        if list(actual_rank.values())[0]==list(predicted_rank.values())[0]:
            ndcg_scores.append(1)
        else:
            ndcg_scores.append(ndcg_penality)
# Prepare for nDCG calculation
average_ndcg = np.mean(ndcg_scores)
print(f"Average nDCG: {average_ndcg}")

from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/data', methods=['POST'])
def receive_data():
    data = request.json  # Extract the JSON data sent
    return jsonify({"received": True, "data": str([avg_bi, avg_bu, avg_up, avg_qi])}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5004)

