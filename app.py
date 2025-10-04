import os
import tempfile
import joblib
from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import pandas as pd
import librosa
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline

# -----------------------------
# Label Map
# -----------------------------
LABEL_MAP = {
    0: "Asthma",
    1: "Bronchiectasis",
    2: "Bronchiolitis",
    3: "COPD",
    4: "Pneumonia",
    5: "LRTI",
    6: "Healthy",
    7: "URTI"
}

# -----------------------------
# Custom Transformers
# -----------------------------
class AudioLoader(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        result = {}
        for file_path in X:
            filename = os.path.basename(file_path)
            y, sr = librosa.load(file_path, mono=True)
            result[filename] = {'data': y, 'sample_rate': sr}
        return result


class AudioTrimmer(BaseEstimator, TransformerMixin):
    def __init__(self, target_duration=7.856):
        self.target_duration = target_duration

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        trimmed = {}
        for filename, audio_info in X.items():
            target_samples = int(self.target_duration * audio_info['sample_rate'])
            data = audio_info['data']
            if len(data) < target_samples:
                data = np.pad(data, (0, target_samples - len(data)))
            else:
                data = data[:target_samples]
            trimmed[filename] = {
                'data': data,
                'sample_rate': audio_info['sample_rate'],
                'duration': self.target_duration
            }
        return trimmed


class FeatureExtractor(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        features = {}
        for filename, audio_info in X.items():
            y_audio = audio_info['data']
            sr = audio_info['sample_rate']
            features[filename] = {
                'chroma_stft': librosa.feature.chroma_stft(y=y_audio, sr=sr),
                'mfcc': librosa.feature.mfcc(y=y_audio, sr=sr, n_mfcc=13),
                'mel_spectrogram': librosa.feature.melspectrogram(y=y_audio, sr=sr),
                'spectral_contrast': librosa.feature.spectral_contrast(y=y_audio, sr=sr),
                'spectral_centroid': librosa.feature.spectral_centroid(y=y_audio, sr=sr),
                'spectral_bandwidth': librosa.feature.spectral_bandwidth(y=y_audio, sr=sr),
                'spectral_rolloff': librosa.feature.spectral_rolloff(y=y_audio, sr=sr),
                'zero_crossing_rate': librosa.feature.zero_crossing_rate(y=y_audio)
            }
        return features


class FeatureStatisticsCalculator(BaseEstimator, TransformerMixin):
    def __init__(self, excluded_features=None):
        self.excluded_features = excluded_features or []

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        feature_stats = []
        for filename, features in X.items():
            file_stats = {'filename': filename}
            for feature_name, data in features.items():
                file_stats[f'{feature_name}_mean'] = np.mean(data)
                file_stats[f'{feature_name}_std'] = np.std(data)
                file_stats[f'{feature_name}_max'] = np.max(data)
                file_stats[f'{feature_name}_min'] = np.min(data)
            feature_stats.append(file_stats)

        df = pd.DataFrame(feature_stats)
        for feature in self.excluded_features:
            if feature in df.columns:
                df.drop(feature, axis=1, inplace=True)
        return df.select_dtypes(exclude=['object'])


def create_pipeline():
    excluded_features = ['mel_spectrogram_min', 'chroma_stft_max']
    return Pipeline([
        ('load_audio', AudioLoader()),
        ('trim_audio', AudioTrimmer()),
        ('extract_features', FeatureExtractor()),
        ('calc_stats', FeatureStatisticsCalculator(excluded_features=excluded_features))
    ])


def predict_condition(wav_file_path, model_path='respiratory_classifier.pkl'):
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")
    model = joblib.load(model_path)
    pipeline = create_pipeline()
    features_df = pipeline.transform([wav_file_path])
    prediction = model.predict(features_df)[0]
    probabilities = model.predict_proba(features_df)[0]
    max_prob = np.max(probabilities)
    classes = model.classes_
    return {
        'prediction': LABEL_MAP.get(int(prediction), str(prediction)),
        'probability': float(max_prob),
        'all_probabilities': {
            LABEL_MAP.get(int(c), str(c)): float(p)
            for c, p in zip(classes, probabilities)
        }
    }

# -----------------------------
# Flask App
# -----------------------------
app = Flask(__name__)
CORS(app)

@app.route("/predict", methods=["POST"])
def predict():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, file.filename)
    file.save(file_path)

    try:
        result = predict_condition(file_path)
        return jsonify(result)
    except Exception as e:
        import traceback
        print("Error during prediction:\n", traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# -----------------------------
# Run App
# -----------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use Render's port or default to 5000
    app.run(host="0.0.0.0", port=port)