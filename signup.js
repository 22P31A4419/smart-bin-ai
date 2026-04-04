document.getElementById("signupForm").addEventListener("submit", async (e) => {
    e.preventDefault(); // prevent default form submission

    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    try {
        const response = await fetch("/signup", {  // Relative URL
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (response.ok) {
            alert(data.message); // Signup successful
            window.location.href = "/login_page"; // Redirect to login page
        } else {
            alert(data.message || "Signup failed!");
        }
    } catch (err) {
        console.error(err);
        alert("Error connecting to server!");
    }
});