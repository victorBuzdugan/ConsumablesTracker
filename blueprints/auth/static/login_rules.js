addEventListener("DOMContentLoaded", (event) => {
    const username = document.getElementById("name");
    const usernameAlert = document.getElementById("name-alert");
    const userRequirements = document.querySelectorAll(".userrequirements");
    let lengUserBoolean;
    let userLeng = document.querySelector(".userleng");
    
    const password = document.getElementById("password");
    const passwordAlert = document.getElementById("password-alert");
    const requirements = document.querySelectorAll(".requirements");
    let lengBoolean;
    let leng = document.querySelector(".leng");

    const submit_button = document.getElementById("submit_button");
    let okName, okPass;

    userRequirements.forEach((element) => element.classList.add("wrong"));
    requirements.forEach((element) => element.classList.add("wrong"));

    username.addEventListener("focus", () => {
        usernameAlert.classList.remove("d-none");
        if (!username.classList.contains("is-valid")) {
            username.classList.add("is-invalid");
        }
    });
    password.addEventListener("focus", () => {
        passwordAlert.classList.remove("d-none");
        if (!password.classList.contains("is-valid")) {
            password.classList.add("is-invalid");
        }
    });

    username.addEventListener("input", () => {
        let value = username.value;
        if (value.length < 1) {
            lengUserBoolean = false;
            okName = false;
        } else if (value.length > 0) {
            lengUserBoolean = true;
            okName = true;
        }

        if (lengUserBoolean == true) {
            username.classList.remove("is-invalid");
            username.classList.add("is-valid");
            usernameAlert.classList.add("d-none");

            userRequirements.forEach((element) => {
                element.classList.remove("wrong");
                element.classList.add("good");
            });
        } else {
            username.classList.remove("is-valid");
            username.classList.add("is-invalid");
            usernameAlert.classList.remove("d-none");

            if (lengUserBoolean == false) {
                userLeng.classList.add("wrong");
                userLeng.classList.remove("good");
            } else {
                userLeng.classList.add("good");
                userLeng.classList.remove("wrong");
            }
        }
        if (okName == true && okPass == true) {
            submit_button.removeAttribute("disabled");
        } else {
            submit_button.setAttribute("disabled", "");
        };
    });

    password.addEventListener("input", () => {
        let value = password.value;
        if (value.length < 1) {
            lengBoolean = false;
            okPass = false;
        } else if (value.length > 0) {
            lengBoolean = true;
            okPass = true;
        }

        if (lengBoolean == true) {
            password.classList.remove("is-invalid");
            password.classList.add("is-valid");
            passwordAlert.classList.add("d-none");

            requirements.forEach((element) => {
                element.classList.remove("wrong");
                element.classList.add("good");
            });
        } else {
            password.classList.remove("is-valid");
            password.classList.add("is-invalid");
            passwordAlert.classList.remove("d-none");


            if (lengBoolean == false) {
                leng.classList.add("wrong");
                leng.classList.remove("good");
            } else {
                leng.classList.add("good");
                leng.classList.remove("wrong");
            }
        }
        if (okName == true && okPass == true) {
            submit_button.removeAttribute("disabled");
        } else {
            submit_button.setAttribute("disabled", "");
        };
    });
    
    
    username.addEventListener("blur", () => {
        usernameAlert.classList.add("d-none");
    });
    
    password.addEventListener("blur", () => {
        passwordAlert.classList.add("d-none");
    });
});