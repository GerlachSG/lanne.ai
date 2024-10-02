import { initializeApp } from "https://www.gstatic.com/firebasejs/10.13.2/firebase-app.js";
import { getAuth, GoogleAuthProvider, signInWithPopup, FacebookAuthProvider } from "https://www.gstatic.com/firebasejs/10.13.2/firebase-auth.js";

// Inicialize o Firebase
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
auth.languageCode = 'en';
const googleprovider = new GoogleAuthProvider();
const facebookprovider = new FacebookAuthProvider();

// Adiciona o listener no botão "entrar" para exibir os botões de login
document.querySelector('.card-button').addEventListener('click', function() {
  // Altera o conteúdo do card ao clicar no botão "entrar"
  const card = document.querySelector('.card');
  card.innerHTML = `
    <h5>Bem Vindo!</h5>
    <img src="seta_vetor.svg" alt="Icone" id="backButton" class="card-icon">
    <div class="button-wrapper2">
      <button class="login-button facebook">
        <img src="facebook-icon.svg" alt="Facebook" class="icon">
        Faça login com<span class="bold-text">Facebook</span>
      </button>
      <button class="login-button google">
        <img src="google-icon.svg" alt="Google" class="icon">
        Faça login com<span class="bold-text">Google</span>
      </button>
    </div>
  `;
 // Animação de voltar do card - Edu
  document.getElementById('backButton').addEventListener('click', function() {
    document.getElementById('card').classList.toggle('show');
    document.getElementById('title').classList.remove('hide');
    document.getElementById('subtitle').classList.remove('hide');
    document.getElementById('showCardBtn').classList.remove('hide');

    // Oculta o título "Lanne.ai" no lado esquerdo
    document.getElementById('left-title').classList.remove('show');
    document.getElementById('left-title').classList.add('hide');
});

  // Agora que o botão Google foi inserido no DOM, adiciona o event listener
  const googleLogin = document.querySelector(".login-button.google");
  googleLogin.addEventListener("click", function() {

    facebooklogin.classList.add("active-login");

    signInWithPopup(auth, googleprovider)
      .then((result) => {
        const credential = GoogleAuthProvider.credentialFromResult(result);
        const user = result.user;
        console.log(user);
         // PARTE DE REDIRECIONAR
        window.location.href = "../logged.html"; // Redireciona após o login
      })
      .catch((error) => {
        const errorCode = error.code;
        const errorMessage = error.message;
        console.error(errorMessage);
      });
  });

  const facebooklogin = document.querySelector(".login-button.facebook");
  facebooklogin.addEventListener("click", function(){
    event.preventDefault();
    signInWithPopup(auth, facebookprovider)
  .then((result) => {
    const user = result.user;
    const credential = FacebookAuthProvider.credentialFromResult(result);
    const accessToken = credential.accessToken;

    console.log(user);
     // PARTE DE REDIRECIONAR
    window.location.href = "login.html";

  })
  .catch((error) => {
    const errorCode = error.code;
    const errorMessage = error.message;
    const email = error.customData.email;
    const credential = FacebookAuthProvider.credentialFromError(error);

  });

  })
});
