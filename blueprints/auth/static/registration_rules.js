addEventListener("DOMContentLoaded", (event) => {
    const username = document.getElementById("name");
    const usernameAlert = document.getElementById("name-alert");
    const userRequirements = document.querySelectorAll(".userrequirements");
    let lengUserBoolean;
    let userLeng = document.querySelector(".userleng");
    
    const confirm = document.getElementById("confirm");
    const confirmAlert = document.getElementById("confirm-alert");
    const confirmRequirements = document.querySelectorAll(".confirmrequirements");
    let equalConfirmBoolean;
    let confirmEqual = document.querySelector(".confirmequal");

    const password = document.getElementById("password");
    const passwordAlert = document.getElementById("password-alert");
    const requirements = document.querySelectorAll(".requirements");
    let lengBoolean, bigLetterBoolean, numBoolean, specialCharBoolean;
    let leng = document.querySelector(".leng");
    let bigLetter = document.querySelector(".big-letter");
    let num = document.querySelector(".num");
    let specialChar = document.querySelector(".special-char");
    const specialChars = "!@#$%^&*_=+";
    const numbers = "0123456789";

    const submit_button = document.getElementById("submit_button");
    let okName, okPass, okConf;

    userRequirements.forEach((element) => element.classList.add("wrong"));
    confirmRequirements.forEach((element) => element.classList.add("wrong"));
    requirements.forEach((element) => element.classList.add("wrong"));

    username.addEventListener("focus", () => {
        usernameAlert.classList.remove("d-none");
        if (!username.classList.contains("is-valid")) {
            username.classList.add("is-invalid");
        }
    });
    confirm.addEventListener("focus", () => {
        confirmAlert.classList.remove("d-none");
        if (!confirm.classList.contains("is-valid")) {
            confirm.classList.add("is-invalid");
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
        if (value.length < 3) {
            lengUserBoolean = false;
            okName = false;
        } else if (value.length > 2) {
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
        if (okName == true && okPass == true && okConf == true) {
            submit_button.removeAttribute("disabled");
        } else {
            submit_button.setAttribute("disabled", "");
        };
    });
    
    confirm.addEventListener("input", () => {
        let value = confirm.value;
        let passvalue = password.value;
        if (value == passvalue && value.length > 7) {
            equalConfirmBoolean = true;
            okConf = true;
        } else {
            equalConfirmBoolean = false;
            okConf = false;
        }

        if (equalConfirmBoolean == true) {
            confirm.classList.remove("is-invalid");
            confirm.classList.add("is-valid");
            confirmAlert.classList.add("d-none");

            confirmRequirements.forEach((element) => {
                element.classList.remove("wrong");
                element.classList.add("good");
                confirmAlert.classList.remove("d-none");
            });
        } else {
            confirm.classList.remove("is-valid");
            confirm.classList.add("is-invalid");

            if (equalConfirmBoolean == false) {
                confirmEqual.classList.add("wrong");
                confirmEqual.classList.remove("good");
            } else {
                confirmEqual.classList.add("good");
                confirmEqual.classList.remove("wrong");
            }
        }
        if (okName == true && okPass == true && okConf == true) {
            submit_button.removeAttribute("disabled");
        } else {
            submit_button.setAttribute("disabled", "");
        };
    });

    password.addEventListener("input", () => {
        let value = password.value;
        if (value.length < 8) {
            lengBoolean = false;
        } else if (value.length > 7) {
            lengBoolean = true;
        }

        if (value.toLowerCase() == value) {
            bigLetterBoolean = false;
        } else {
            bigLetterBoolean = true;
        }

        numBoolean = false;
        for (let i = 0; i < value.length; i++) {
            for (let j = 0; j < numbers.length; j++) {
                if (value[i] == numbers[j]) {
                    numBoolean = true;
                }
            }
        }

        specialCharBoolean = false;
        for (let i = 0; i < value.length; i++) {
            for (let j = 0; j < specialChars.length; j++) {
                if (value[i] == specialChars[j]) {
                    specialCharBoolean = true;
                }
            }
        }

        if (lengBoolean == true && bigLetterBoolean == true && numBoolean == true && specialCharBoolean == true) {
            password.classList.remove("is-invalid");
            password.classList.add("is-valid");
            passwordAlert.classList.add("d-none");
            okPass = true;

            requirements.forEach((element) => {
                element.classList.remove("wrong");
                element.classList.add("good");
            });
        } else {
            password.classList.remove("is-valid");
            password.classList.add("is-invalid");
            passwordAlert.classList.remove("d-none");
            okPass = false;


            if (lengBoolean == false) {
                leng.classList.add("wrong");
                leng.classList.remove("good");
            } else {
                leng.classList.add("good");
                leng.classList.remove("wrong");
            }

            if (bigLetterBoolean == false) {
                bigLetter.classList.add("wrong");
                bigLetter.classList.remove("good");
            } else {
                bigLetter.classList.add("good");
                bigLetter.classList.remove("wrong");
            }

            if (numBoolean == false) {
                num.classList.add("wrong");
                num.classList.remove("good");
            } else {
                num.classList.add("good");
                num.classList.remove("wrong");
            }

            if (specialCharBoolean == false) {
                specialChar.classList.add("wrong");
                specialChar.classList.remove("good");
            } else {
                specialChar.classList.add("good");
                specialChar.classList.remove("wrong");
            }
        }
        if (okName == true && okPass == true && okConf == true) {
            submit_button.removeAttribute("disabled");
        } else {
            submit_button.setAttribute("disabled", "");
        };
    });

    
    username.addEventListener("blur", () => {
        usernameAlert.classList.add("d-none");
    });
    
    confirm.addEventListener("blur", () => {
        confirmAlert.classList.add("d-none");
    });

    password.addEventListener("blur", () => {
        passwordAlert.classList.add("d-none");
    });
});