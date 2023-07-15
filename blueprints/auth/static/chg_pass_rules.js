addEventListener("DOMContentLoaded", (event) => {

    const old_password = document.getElementById("old_password");
    const old_passwordAlert = document.getElementById("old_password-alert");
    const old_passwordRequirements = document.querySelectorAll(".old_passwordrequirements");
    let presentOldPasswordBoolean;
    let confirmpresent = document.querySelector(".confirmpresent");

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

    const submit_button = document.getElementById("submit");
    let okOldPass, okPass, okConf;

    old_passwordRequirements.forEach((element) => element.classList.add("wrong"));
    confirmRequirements.forEach((element) => element.classList.add("wrong"));
    requirements.forEach((element) => element.classList.add("wrong"));

    old_password.addEventListener("focus", () => {
        old_passwordAlert.classList.remove("d-none");
        if (!old_password.classList.contains("is-valid")) {
            old_password.classList.add("is-invalid");
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

    old_password.addEventListener("input", () => {
        let value = old_password.value;

        if (value.length < 8) {
            presentOldPasswordBoolean = false;
            okOldPass = false;
        } else if (value.length > 7) {
            presentOldPasswordBoolean = true;
            okOldPass = true;
        }

        if (presentOldPasswordBoolean == true) {
            old_password.classList.remove("is-invalid");
            old_password.classList.add("is-valid");
            old_passwordAlert.classList.add("d-none");

            old_passwordRequirements.forEach((element) => {
                element.classList.remove("wrong");
                element.classList.add("good");
            });
        } else {
            old_password.classList.remove("is-valid");
            old_password.classList.add("is-invalid");
            old_passwordAlert.classList.remove("d-none");

            if (presentOldPasswordBoolean == false) {
                confirmpresent.classList.add("wrong");
                confirmpresent.classList.remove("good");
            } else {
                confirmpresent.classList.add("good");
                confirmpresent.classList.remove("wrong");
            }
        }
        if (okOldPass == true && okPass == true && okConf == true) {
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
            });
        } else {
            confirm.classList.remove("is-valid");
            confirm.classList.add("is-invalid");
            confirmAlert.classList.remove("d-none");

            if (equalConfirmBoolean == false) {
                confirmEqual.classList.add("wrong");
                confirmEqual.classList.remove("good");
            } else {
                confirmEqual.classList.add("good");
                confirmEqual.classList.remove("wrong");
            }
        }
        if (okOldPass == true && okPass == true && okConf == true) {
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
        if (okOldPass == true && okPass == true && okConf == true) {
            submit_button.removeAttribute("disabled");
        } else {
            submit_button.setAttribute("disabled", "");
        };
    });

    
    old_password.addEventListener("blur", () => {
        old_passwordAlert.classList.add("d-none");
    });

    confirm.addEventListener("blur", () => {
        confirmAlert.classList.add("d-none");
    });

    password.addEventListener("blur", () => {
        passwordAlert.classList.add("d-none");
    });
});