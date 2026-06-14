from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2

app = FastAPI(title="RFID Cashless System")
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
from fastapi import Form

DB_CONFIG = {
    "host": "localhost",
    "database": "rfid_system",
    "user": "postgres",
    "password": "mysecretpassword"
}


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


class DebitRequest(BaseModel):
    uid: str
    amount: float


class CreditRequest(BaseModel):
    uid: str
    amount: float


class RegisterRequest(BaseModel):
    uid: str
    name: str
    balance: float = 0

@app.get("/admin", response_class=HTMLResponse)
def admin():

    return """
<!DOCTYPE html>
<html>
<head>
    <title>RFID Admin</title>
</head>
<body>

<h1>RFID Admin Dashboard</h1>

<button id="connectBtn">
Connect ESP32
</button>

<br><br>

<form id="adminForm">

    UID:<br>
    <input id="uid" name="uid" ><br><br>

    Name (for new cards):<br>
    <input id="name" name="name"><br><br>

    Amount:<br>
    <input id="amount"
           name="amount"
           type="number"
           step="0.01"
           required><br><br>

    <button type="submit">
        Submit
    </button>

</form>

<hr>

<div id="result"></div>

<script>
async function lookupUID(uid) {

    if (!uid) return;

    try {

        const response =
            await fetch("/balance/" + uid);

        if (response.ok) {

            const data =
                await response.json();

            document
                .getElementById("name")
                .value = data.name;

            document
                .getElementById("result")
                .innerHTML =
                `
                <h3>Card Found</h3>
                <p>Name: ${data.name}</p>
                <p>Current Balance:
                ₹${data.balance.toFixed(2)}</p>
                `;

        } else {

            document
                .getElementById("name")
                .value = "";

            document
                .getElementById("result")
                .innerHTML =
                `
                <h3>New Card</h3>
                <p>No account found.</p>
                `;
        }

    } catch(err) {

        console.error(err);
    }
}
document.getElementById("connectBtn")
.addEventListener("click", async () => {

    try {

        const port =
            await navigator.serial.requestPort();

        await port.open({
            baudRate: 115200
        });

        const decoder =
            new TextDecoderStream();

        port.readable.pipeTo(
            decoder.writable
        );

        const reader =
            decoder.readable.getReader();

        let buffer = "";

        while (true) {

            const { value, done } =
                await reader.read();

            if (done) break;

            buffer += value;

            let lines =
                buffer.split("\\n");

            buffer = lines.pop();

            for (let line of lines) {

                line = line.trim();

                console.log(line);

                if (line.startsWith("UID:")) {

                    let uid =
                        line.substring(4).trim();

                    document
                        .getElementById("uid")
                        .value = uid;
                        lookupUID(uid);
                }
            }
        }

    } catch(err) {

        console.error(err);

        alert(
            "Failed to connect ESP32"
        );
    }
});

document.getElementById("adminForm")
.addEventListener("submit", async (e) => {

    e.preventDefault();

    const formData = new FormData();

    formData.append(
        "uid",
        document.getElementById("uid").value
    );

    formData.append(
        "name",
        document.getElementById("name").value
    );

    formData.append(
        "amount",
        document.getElementById("amount").value
    );

    try {

        const response =
            await fetch(
                "/admin_action",
                {
                    method: "POST",
                    body: formData
                }
            );

        const data =
            await response.json();

        document.getElementById("result")
        .innerHTML =
        `
        <h2>Success</h2>

        <p><b>Action:</b> ${data.action}</p>

        <p><b>Balance:</b>
        ₹${data.balance.toFixed(2)}</p>
        `;

    } catch(err) {

        console.error(err);

        document.getElementById("result")
        .innerHTML =
        `
        <h2>Error</h2>
        <p>${err}</p>
        `;
    }

});

document
.getElementById("uid")
.addEventListener("change", function() {

    lookupUID(this.value);

});

</script>

</body>
</html>
"""
@app.get("/transactions_json")
def transactions_json():

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            t.id,
            u.name,
            t.uid,
            t.type,
            t.amount,
            t.created_at
        FROM transactions t
        JOIN users u
        ON t.uid = u.uid
        ORDER BY t.id DESC
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [
        {
            "id": r[0],
            "name": r[1],
            "uid": r[2],
            "type": r[3],
            "amount": float(r[4]),
            "time": str(r[5])
        }
        for r in rows
    ]

@app.get("/transactions_page", response_class=HTMLResponse)
def transactions_page():

    return """
<!DOCTYPE html>
<html>

<head>

<title>Transaction History</title>

<style>

body{
    font-family: Arial;
    margin:20px;
}

table{
    border-collapse: collapse;
    width:100%;
}

th,td{
    border:1px solid black;
    padding:8px;
    text-align:center;
}

th{
    background:#f0f0f0;
}

.credit{
    color:green;
    font-weight:bold;
}

.debit{
    color:red;
    font-weight:bold;
}

</style>

</head>

<body>

<h1>Transaction History</h1>

<table>

<thead>

<tr>
    <th>SL No</th>
    <th>Name</th>
    <th>UID</th>
    <th>Type</th>
    <th>Amount</th>
    <th>Date & Time</th>
</tr>

</thead>

<tbody id="txnBody">

</tbody>

</table>

<script>

async function loadTransactions() {

    try {

        const response =
            await fetch("/transactions_json");

        const data =
            await response.json();

        let html = "";

        data.forEach(txn => {

            html += `
            <tr>
                <td>${txn.id}</td>
                <td>${txn.name}</td>
                <td>${txn.uid}</td>

                <td class="${txn.type}">
                    ${txn.type.toUpperCase()}
                </td>

                <td>
                    ₹${txn.amount.toFixed(2)}
                </td>

                <td>
                    ${txn.time}
                </td>

            </tr>
            `;
        });

        document
            .getElementById("txnBody")
            .innerHTML = html;

    }
    catch(err){

        console.error(err);

    }
}

loadTransactions();

setInterval(loadTransactions, 3000);

</script>

</body>
</html>
"""

@app.post("/admin_action")
def admin_action(
    uid: str = Form(...),
    name: str = Form(""),
    amount: float = Form(...)
):

    conn = get_conn()
    cur = conn.cursor()

    try:

        cur.execute(
            """
            SELECT balance
            FROM users
            WHERE uid=%s
            """,
            (uid,)
        )

        row = cur.fetchone()

        if row:
            # Existing user -> Recharge

            cur.execute(
                """
                UPDATE users
                SET balance = balance + %s
                WHERE uid = %s
                RETURNING balance
                """,
                (amount, uid)
            )

            new_balance = float(cur.fetchone()[0])

            cur.execute(
                """
                INSERT INTO transactions(uid,type,amount)
                VALUES(%s,'credit',%s)
                """,
                (uid, amount)
            )

            action = "recharged"

        else:
            # New user -> Create

            cur.execute(
                """
                INSERT INTO users(uid,name,balance)
                VALUES(%s,%s,%s)
                """,
                (uid, name, amount)
            )

            cur.execute(
                """
                INSERT INTO transactions(uid,type,amount)
                VALUES(%s,'credit',%s)
                """,
                (uid, amount)
            )

            new_balance = amount
            action = "created"

        conn.commit()

        return {
            "success": True,
            "action": action,
            "balance": new_balance
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(500, str(e))

    finally:
        cur.close()
        conn.close()

@app.post("/register")
def register(req: RegisterRequest):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO users(uid,name,balance)
        VALUES(%s,%s,%s)
        """,
        (req.uid, req.name, req.balance)
    )

    conn.commit()

    cur.close()
    conn.close()

    return {"success": True}

@app.get("/")
def root():
    return {"status": "online"}


@app.get("/balance/{uid}")
def get_balance(uid: str):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "SELECT name,balance FROM users WHERE uid=%s",
        (uid,)
    )

    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        raise HTTPException(404, "Card not found")

    return {
        "uid": uid,
        "name": row[0],
        "balance": float(row[1])
    }


@app.post("/credit")
def credit(req: CreditRequest):

    conn = get_conn()
    cur = conn.cursor()

    try:

        cur.execute(
            """
            SELECT balance
            FROM users
            WHERE uid=%s
            FOR UPDATE
            """,
            (req.uid,)
        )

        row = cur.fetchone()

        if not row:
            raise HTTPException(404, "Card not found")

        new_balance = float(row[0]) + req.amount

        cur.execute(
            """
            UPDATE users
            SET balance=%s
            WHERE uid=%s
            """,
            (new_balance, req.uid)
        )

        cur.execute(
            """
            INSERT INTO transactions(uid,type,amount)
            VALUES(%s,'credit',%s)
            """,
            (req.uid, req.amount)
        )

        conn.commit()

        return {
            "success": True,
            "balance": new_balance
        }

    except:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


@app.post("/debit")
def debit(req: DebitRequest):

    conn = get_conn()
    cur = conn.cursor()

    try:

        cur.execute(
            """
            SELECT balance
            FROM users
            WHERE uid=%s
            FOR UPDATE
            """,
            (req.uid,)
        )

        row = cur.fetchone()

        if not row:
            raise HTTPException(404, "Card not found")

        current_balance = float(row[0])

        if current_balance < req.amount:
            raise HTTPException(
                400,
                "Insufficient balance"
            )

        new_balance = current_balance - req.amount

        cur.execute(
            """
            UPDATE users
            SET balance=%s
            WHERE uid=%s
            """,
            (new_balance, req.uid)
        )

        cur.execute(
            """
            INSERT INTO transactions(uid,type,amount)
            VALUES(%s,'debit',%s)
            """,
            (req.uid, req.amount)
        )

        conn.commit()

        return {
            "success": True,
            "balance": new_balance
        }

    except:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


@app.get("/transactions/{uid}")
def get_transactions(uid: str):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT type, amount, created_at
        FROM transactions
        WHERE uid=%s
        ORDER BY created_at DESC
        LIMIT 50
        """,
        (uid,)
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [
        {
            "type": r[0],
            "amount": float(r[1]),
            "time": r[2]
        }
        for r in rows
    ]