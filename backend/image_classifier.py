"""
image_classifier.py — Face Detection + Image Classification
=====================================================
Uses Haar cascades for face detection (human), then ResNet50 for animals/objects.
Classifies captured images into 3 categories: 'human', 'animal', 'object'
"""

import torch
import torchvision.transforms as transforms
from torchvision.models import resnet50
from PIL import Image
import numpy as np
import threading
import cv2

# Global model and lock (single instance)
MODEL = None
DEVICE = None
MODEL_LOCK = threading.Lock()
TRANSFORM = None
FACE_CASCADE = None
ANIMAL_CONFIDENCE_THRESHOLD = 0.3

# ImageNet class indices for animals (humans handled by face detection)
ANIMAL_CLASSES = {
    # Mammals
    207,   # golden_retriever (dogs)
    208,   # Labrador_retriever
    209,   # poodle
    215,   # brittany_spaniel
    217,   # cocker_spaniel
    220,   # English_cocker_spaniel
    222,   # English_springer_spaniel
    226,   # french_bulldog
    229,   # german_shepherd
    250,   # siberian_husky
    258,   # pointer
    273,   # weimaraner
    281,   # tabby
    282,   # tiger_cat
    283,   # persian_cat
    284,   # siamese_cat
    285,   # cat (generic)
    293,   # lion
    294,   # tiger
    295,   # leopard
    296,   # snow_leopard
    297,   # jaguar
    298,   # puma
    299,   # lynx
    # Primates (excluding humans, handled by face detection)
    365,   # chimpanzee
    366,   # gibbon
    367,   # gorilla
    368,   # orangutan
    369,   # macaque
    370,   # baboon
    # Other animals
    7,     # frog
    8,     # toad
    21,    # chickadee
    22,    # pelican
    85,    # bullfrog
    86,    # tree_frog
    323,   # elephant
    325,   # hippopotamus
    326,   # deer
    327,   # moose
    328,   # elk
    329,   # pronghorn
    330,   # bighorn
    331,   # ibex
    332,   # hartebeest
    333,   # impala
    334,   # gazelle
    335,   # arabian_camel
    336,   # llama
    337,   # weasel
    338,   # mink
    339,   # polecat
    340,   # black-footed_ferret
    341,   # otter
    342,   # skunk
    343,   # badger
    344,   # armadillo
    345,   # pangolin
}

ANIMAL_CLASSES = {
    # Mammals
    207,   # golden_retriever (dogs)
    208,   # Labrador_retriever
    209,   # poodle
    215,   # brittany_spaniel
    217,   # cocker_spaniel
    220,   # English_cocker_spaniel
    222,   # English_springer_spaniel
    226,   # french_bulldog
    229,   # german_shepherd
    250,   # siberian_husky
    258,   # pointer
    273,   # weimaraner
    281,   # tabby
    282,   # tiger_cat
    283,   # persian_cat
    284,   # siamese_cat
    285,   # cat (generic)
    293,   # lion
    294,   # tiger
    295,   # leopard
    296,   # snow_leopard
    297,   # jaguar
    298,   # puma
    299,   # lynx
    # Primates
    365,   # chimpanzee
    366,   # gibbon
    367,   # gorilla
    368,   # orangutan
    369,   # macaque
    370,   # baboon
    # Other animals
    7,     # frog
    8,     # toad
    21,    # chickadee
    22,    # pelican
    85,    # bullfrog
    86,    # tree_frog
    323,   # elephant
    325,   # hippopotamus
    326,   # deer
    327,   # moose
    328,   # elk
    329,   # pronghorn
    330,   # bighorn
    331,   # ibex
    332,   # hartebeest
    333,   # impala
    334,   # gazelle
    335,   # arabian_camel
    336,   # llama
    337,   # weasel
    338,   # mink
    339,   # polecat
    340,   # black-footed_ferret
    341,   # otter
    342,   # skunk
    343,   # badger
    344,   # armadillo
    345,   # pangolin
}

def _init_model():
    """Initialize ResNet50 model and face cascade (called once at first use)."""
    global MODEL, DEVICE, TRANSFORM, FACE_CASCADE
    
    if MODEL is not None:
        return
    
    with MODEL_LOCK:
        if MODEL is not None:  # Double-check after lock
            return
        
        print("[🧠 Classifier] Loading ResNet50 model and face cascade...")
        try:
            DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            print(f"[🧠 Classifier] Using device: {DEVICE}")
            
            # Load pre-trained ResNet50
            MODEL = resnet50(weights='ResNet50_Weights.IMAGENET1K_V2')
            MODEL = MODEL.to(DEVICE)
            MODEL.eval()
            
            # Standard ImageNet normalization
            TRANSFORM = transforms.Compose([
                transforms.Resize((256, 256)),
                transforms.CenterCrop((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                ),
            ])
            
            # Load Haar cascade for face detection
            FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            if FACE_CASCADE.empty():
                print("[⚠️ Classifier] Warning: Could not load face cascade")
            else:
                print("[✓ Classifier] Face cascade loaded")
            
            print("[✓ Classifier] Model loaded successfully")
        except Exception as e:
            print(f"[✗ Classifier] Failed to load model: {e}")
            raise


def classify_image(frame_cv2) -> str:
    """
    Classify a single image frame into 'human', 'animal', or 'object'.
    
    Uses face detection for humans, ResNet50 for animals/objects.
    
    Args:
        frame_cv2: OpenCV frame (numpy array, BGR format)
    
    Returns:
        str: One of 'human', 'animal', 'object'
    """
    _init_model()
    
    try:
        # Step 1: Face detection for humans
        gray = cv2.cvtColor(frame_cv2, cv2.COLOR_BGR2GRAY)
        faces = FACE_CASCADE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        
        if len(faces) > 0:
            print(f"[🧠 Classifier] Detected {len(faces)} face(s) - classifying as 'human'")
            return "human"
        
        # Step 2: If no face detected, use ResNet50 for animals/objects
        print("[🧠 Classifier] No face detected - using ResNet50 for classification")
        
        # Convert BGR (OpenCV) to RGB (PIL)
        rgb_frame = frame_cv2[:, :, ::-1]
        pil_image = Image.fromarray(rgb_frame)
        
        # Preprocess
        input_tensor = TRANSFORM(pil_image).unsqueeze(0).to(DEVICE)
        
        # Inference
        with torch.no_grad():
            outputs = MODEL(input_tensor)
            probabilities = torch.softmax(outputs, dim=1)
            top_prob, top_class = torch.max(probabilities, dim=1)
            class_idx = top_class.item()
            confidence = top_prob.item()
        
        print(f"[🧠 Classifier] Top class: {class_idx}, Confidence: {confidence:.2%}")
        
        # Classify into 'animal' or 'object'
        if class_idx in ANIMAL_CLASSES and confidence >= ANIMAL_CONFIDENCE_THRESHOLD:
            return "animal"
        else:
            return "object"
    
    except Exception as e:
        print(f"[✗ Classifier] Classification error: {e}")
        return "object"  # Safe fallback


def get_classification_confidence(frame_cv2) -> dict:
    """
    Get full classification result with confidence and details.
    
    Returns:
        dict: {
            'category': 'human' | 'animal' | 'object',
            'confidence': float,
            'details': str
        }
    """
    _init_model()
    
    try:
        # Step 1: Face detection
        gray = cv2.cvtColor(frame_cv2, cv2.COLOR_BGR2GRAY)
        faces = FACE_CASCADE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        
        if len(faces) > 0:
            return {
                "category": "human",
                "confidence": 1.0,  # Face detection is binary
                "details": f"Face detected ({len(faces)} faces)",
            }
        
        # Step 2: ResNet50 classification
        rgb_frame = frame_cv2[:, :, ::-1]
        pil_image = Image.fromarray(rgb_frame)
        input_tensor = TRANSFORM(pil_image).unsqueeze(0).to(DEVICE)
        
        with torch.no_grad():
            outputs = MODEL(input_tensor)
            probabilities = torch.softmax(outputs, dim=1)
            top_prob, top_class = torch.max(probabilities, dim=1)
            class_idx = top_class.item()
            confidence = top_prob.item()
        
        # Determine category
        if class_idx in ANIMAL_CLASSES and confidence >= ANIMAL_CONFIDENCE_THRESHOLD:
            category = "animal"
        else:
            category = "object"
        
        return {
            "category": category,
            "confidence": round(confidence, 4),
            "details": f"Class {class_idx}, {confidence:.2%}",
        }
    
    except Exception as e:
        print(f"[✗ Classifier] Confidence retrieval error: {e}")
        return {
            "category": "object",
            "confidence": 0.0,
            "details": "Error",
        }
