from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "assessx-demo-secret"
DB = "assessx.db"

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init_db():
    c=db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,email TEXT UNIQUE,password TEXT,role TEXT DEFAULT 'student');
    CREATE TABLE IF NOT EXISTS subjects(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT UNIQUE);
    CREATE TABLE IF NOT EXISTS questions(id INTEGER PRIMARY KEY AUTOINCREMENT,subject_id INTEGER,question TEXT,a TEXT,b TEXT,c TEXT,d TEXT,answer TEXT);
    CREATE TABLE IF NOT EXISTS results(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,subject_id INTEGER,score INTEGER,total INTEGER,percentage REAL,taken_at TEXT);
    """)
    c.execute("INSERT OR IGNORE INTO users(name,email,password,role) VALUES(?,?,?,?)",("Administrator","admin@assessx.com","admin123","admin"))
    for s in ["Java","DBMS","Computer Networks","Operating System","Data Structures"]:
        c.execute("INSERT OR IGNORE INTO subjects(name) VALUES(?)",(s,))
    for s in ["Java","DBMS","Computer Networks","Operating System","Data Structures"]:
        sid=c.execute("SELECT id FROM subjects WHERE name=?",(s,)).fetchone()["id"]
        if not c.execute("SELECT 1 FROM questions WHERE subject_id=?",(sid,)).fetchone():
            c.execute("INSERT INTO questions(subject_id,question,a,b,c,d,answer) VALUES(?,?,?,?,?,?,?)",(sid,f"Which option is a basic concept related to {s}?","A programming/CS concept","A fruit","A vehicle","A city","A"))
            c.execute("INSERT INTO questions(subject_id,question,a,b,c,d,answer) VALUES(?,?,?,?,?,?,?)",(sid,f"Which option is commonly studied in {s}?","Algorithms and concepts","Cooking","Geography","Music","A"))
    c.commit(); c.close()

@app.route("/")
def index(): return render_template("index.html")

@app.route("/register",methods=["GET","POST"])
def register():
    if request.method=="POST":
        try:
            c=db(); c.execute("INSERT INTO users(name,email,password) VALUES(?,?,?)",(request.form["name"],request.form["email"],request.form["password"])); c.commit(); c.close()
            flash("Registration successful."); return redirect(url_for("login"))
        except sqlite3.IntegrityError: flash("Email already registered.")
    return render_template("register.html")

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        c=db(); u=c.execute("SELECT * FROM users WHERE email=? AND password=?",(request.form["email"],request.form["password"])).fetchone(); c.close()
        if u:
            session.update(user_id=u["id"],name=u["name"],role=u["role"]); return redirect(url_for("dashboard"))
        flash("Invalid login.")
    return render_template("login.html")

@app.route("/logout")
def logout(): session.clear(); return redirect("/")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:return redirect("/login")
    c=db(); subjects=c.execute("SELECT * FROM subjects").fetchall()
    results=c.execute("SELECT r.*,s.name subject FROM results r JOIN subjects s ON s.id=r.subject_id WHERE r.user_id=? ORDER BY r.id DESC",(session["user_id"],)).fetchall(); c.close()
    return render_template("dashboard.html",subjects=subjects,results=results)

@app.route("/test/<int:sid>",methods=["GET","POST"])
def test(sid):
    if "user_id" not in session:return redirect("/login")
    c=db(); subject=c.execute("SELECT * FROM subjects WHERE id=?",(sid,)).fetchone(); qs=c.execute("SELECT * FROM questions WHERE subject_id=?",(sid,)).fetchall()
    if request.method=="POST":
        score=sum(request.form.get(str(q["id"]))==q["answer"] for q in qs); total=len(qs); pct=round(score*100/total,2) if total else 0
        c.execute("INSERT INTO results(user_id,subject_id,score,total,percentage,taken_at) VALUES(?,?,?,?,?,?)",(session["user_id"],sid,score,total,pct,datetime.now().strftime("%Y-%m-%d %H:%M"))); c.commit(); c.close()
        return render_template("result.html",subject=subject,score=score,total=total,pct=pct)
    c.close(); return render_template("test.html",subject=subject,questions=qs)

@app.route("/admin")
def admin():
    if session.get("role")!="admin": return redirect("/dashboard")
    c=db(); subjects=c.execute("SELECT * FROM subjects").fetchall(); users=c.execute("SELECT name,email FROM users WHERE role='student'").fetchall()
    results=c.execute("SELECT r.*,u.name student,s.name subject FROM results r JOIN users u ON u.id=r.user_id JOIN subjects s ON s.id=r.subject_id ORDER BY r.id DESC").fetchall(); c.close()
    return render_template("admin.html",subjects=subjects,users=users,results=results)

@app.route("/admin/add_subject",methods=["POST"])
def add_subject():
    if session.get("role")!="admin": return redirect("/dashboard")
    c=db(); c.execute("INSERT OR IGNORE INTO subjects(name) VALUES(?)",(request.form["name"],)); c.commit(); c.close(); return redirect("/admin")

if __name__=="__main__":
    init_db(); app.run(debug=True)
