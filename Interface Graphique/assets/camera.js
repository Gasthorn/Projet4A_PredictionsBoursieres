// assets/camera.js

// Variables globales
let videoStream = null;
let captureInterval = null;
let isCapturing = false;
let isCameraStarted = false;

// Initialiser la caméra
window.startCamera = function(videoElementId) {
    console.log(" startCamera appelé pour:", videoElementId);
    
    const video = document.getElementById(videoElementId);
    if (!video) {
        console.error(" Élément vidéo non trouvé:", videoElementId);
        return false;
    }
    
    // Si déjà démarrée, ne pas redémarrer
    if (isCameraStarted && videoStream) {
        console.log("Caméra déjà démarrée");
        return true;
    }
    
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ 
            video: {
                width: { ideal: 640 },
                height: { ideal: 480 },
                facingMode: "user"
            } 
        })
        .then(function(stream) {
            videoStream = stream;
            video.srcObject = stream;
            video.play();
            isCameraStarted = true;
            console.log(" Caméra démarrée avec succès");
            
            // Mettre à jour le statut
            const statusDiv = document.getElementById('face-login-status') || 
                             document.getElementById('camera-status');
            if (statusDiv) {
                statusDiv.innerHTML = 'Caméra active';
                statusDiv.className = 'camera-status face-detected';
            }
            
            return true;
        })
        .catch(function(error) {
            console.error("Erreur caméra:", error);
            const statusDiv = document.getElementById('face-login-status') || 
                             document.getElementById('camera-status');
            if (statusDiv) {
                statusDiv.innerHTML = 'Erreur accès caméra: ' + error.message;
                statusDiv.className = 'camera-status no-face';
            }
            return false;
        });
    } else {
        console.error("navigator.mediaDevices non supporté");
        return false;
    }
    return true;
};

// Arrêter la caméra
window.stopCamera = function() {
    console.log("Arrêt de la caméra");
    
    if (videoStream) {
        videoStream.getTracks().forEach(track => {
            track.stop();
            console.log("  - Track arrêtée:", track.kind);
        });
        videoStream = null;
        isCameraStarted = false;
    }
    
    if (captureInterval) {
        clearInterval(captureInterval);
        captureInterval = null;
        isCapturing = false;
    }
    
    // Nettoyer l'élément vidéo
    const videoElements = ['face-login-camera', 'camera-feed'];
    videoElements.forEach(id => {
        const video = document.getElementById(id);
        if (video && video.srcObject) {
            video.srcObject = null;
        }
    });
    
    console.log("Caméra arrêtée");
};

// Capturer une image
window.captureImage = function(videoElementId, callbackId) {
    console.log("captureImage appelé");
    
    const video = document.getElementById(videoElementId);
    
    if (!video || !videoStream || !isCameraStarted) {
        console.log("Caméra pas prête");
        return null;
    }
    
    try {
        const canvas = document.createElement('canvas');
        canvas.width = 320;
        canvas.height = 240;
        
        const context = canvas.getContext('2d');
        
        // Effet miroir
        context.translate(canvas.width, 0);
        context.scale(-1, 1);
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // Convertir en base64
        const imageData = canvas.toDataURL('image/jpeg', 0.8);
        
        console.log("Image capturée");
        return imageData;
        
    } catch (error) {
        console.error("Erreur capture:", error);
        return null;
    }
};

// Démarrer automatiquement sur la page face-login
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM chargé, initialisation...");
    
    // Vérifier toutes les secondes
    var checkInterval = setInterval(function() {
        if (window.location.pathname === '/face-login') {
            console.log("Page face-login détectée");
            
            var videoElement = document.getElementById('face-login-camera');
            if (videoElement && !isCameraStarted) {
                console.log("Démarrage de la caméra...");
                window.startCamera('face-login-camera');
                
                // Mettre à jour le statut
                var statusDiv = document.getElementById('face-login-status');
                if (statusDiv) {
                    statusDiv.innerHTML = 'Caméra activée';
                }
                
                // Une fois démarré, on peut arrêter de vérifier
                clearInterval(checkInterval);
            }
        }
    }, 1000);
});

// Exposer les fonctions pour Dash
window.dash_clientside = window.dash_clientside || {};
window.dash_clientside.camera = {
    start: function(videoId) {
        return window.startCamera(videoId);
    },
    stop: function() {
        return window.stopCamera();
    },
    capture: function(videoId) {
        return window.captureImage(videoId, 'face-login-result');
    }
};

// Fonction pour le callback automatique de Dash
window.dash_clientside.capture = {
    capture: function(n_intervals) {
        if (window.captureImage && isCameraStarted) {
            return window.captureImage('face-login-camera', 'face-login-result');
        }
        return window.dash_clientside.no_update;
    }
};

console.log("camera.js chargé avec succès");