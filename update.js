import { initializeApp } from "https://www.gstatic.com/firebasejs/10.1.0/firebase-app.js";
import { getAuth, GoogleAuthProvider, FacebookAuthProvider, onAuthStateChanged, signInWithPopup } from "https://www.gstatic.com/firebasejs/10.1.0/firebase-auth.js";


const firebaseConfig = {
    apiKey: "AIzaSyCs-wr2q_TIlszjkAZD_xcw1lPL0gts1YU",
    authDomain: "login-lanne.firebaseapp.com",
    projectId: "login-lanne",
    storageBucket: "login-lanne.appspot.com",
    messagingSenderId: "1086334391009",
    appId: "1:1086334391009:web:447dc5dbf6319c9599dda0"
};


const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

// Provedores de Autenticação
const googleProvider = new GoogleAuthProvider();
const facebookProvider = new FacebookAuthProvider();

function updateUserProfile(user) {
    const userProfilePicture = user.photoURL;
    const profilePictureElement = document.getElementById("userProfilePicture");

    if (profilePictureElement && userProfilePicture) {
        profilePictureElement.src = userProfilePicture;
    } else {
        // Defina uma imagem padrão se a URL não estiver disponível
        profilePictureElement.src = 'caminho/para/imagem/padrao.png'; // Substitua pelo caminho da sua imagem padrão
    }
}

// Autenticação com Popup (Google e Facebook)
function signIn(provider) {
    signInWithPopup(auth, provider)
        .then((result) => {
            updateUserProfile(result.user);
        })
        .catch((error) => {
            console.error("Erro durante o login: ", error);
        });
}

// Aguarda o carregamento completo do DOM
document.addEventListener("DOMContentLoaded", () => {
    onAuthStateChanged(auth, (user) => {
        if (user) {
            updateUserProfile(user);
        } else {
            console.log("Nenhum usuário logado");
        }
    });
});


onAuthStateChanged(auth, (user) => {
    if (user) {
        updateUserProfile(user);
    } else {
        console.log("Nenhum usuário logado");
    }
});


