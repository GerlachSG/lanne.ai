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
    const userName = user.displayName;
    const userEmail = user.email;
    const userProfilePicture = user.photoURL;

    document.getElementById("userName").textContent = userName;
    document.getElementById("userEmail").textContent = userEmail;
    document.getElementById("userProfilePicture").src = userProfilePicture;
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


onAuthStateChanged(auth, (user) => {
    if (user) {
        updateUserProfile(user);
    } else {
        console.log("Nenhum usuário logado");
    }
});
