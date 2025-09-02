from flask import Flask, render_template_string, request, redirect, url_for, session
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = 'secret'

products = ["Rice", "Millets", "Pulses", "Oils", "Other"]
estimates_db = {}
users = {
    'admin': {'password': 'adminpass', 'role': 'admin'},
    'analyst': {'password': 'analystpass', 'role': 'analyst'}
}

style = '''<style>
body { font-family: Arial; background: #f4f4f4; margin: 20px; }
form { background: #fff; padding: 20px; border-radius: 8px; max-width: 700px; margin: auto; }
input { padding: 5px; margin: 5px 0; width: 100%; }
button { padding: 10px 20px; background: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer; }
button:hover { background: #218838; }
h2, h3 { color: #333; }
a { text-decoration: none; color: #007bff; }
a:hover { text-decoration: underline; }
table { border-collapse: collapse; width: 100%; background: white; }
th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
th { background-color: #f2f2f2; }
ul { list-style: none; padding: 0; }
li { margin: 5px 0; }
</style>'''

template_login = style + '''
<h2>Login</h2>
<form method="post">
  <input name="username" placeholder="Username">
  <input name="password" type="password" placeholder="Password">
  <button type="submit">Login</button>
</form>
'''

template_dashboard = style + '''
<h2>Dashboard</h2>
<p>Welcome {{ session['username'] }} ({{ session['role'] }})</p>
<a href="{{ url_for('create_estimate') }}">Create Estimate</a><br>
<a href="{{ url_for('view_estimates') }}">View Estimates</a><br>
<a href="{{ url_for('logout') }}">Logout</a>
'''

template_create_estimate = style + '''
<h2>Create New Estimate</h2>
<form method="post">
  Estimate Name: <input name="name"><br>
  Apply Same Margin to All (%): <input name="same_margin" type="number"><br>
  {% for p in products %}
  <h3>{{ p }}</h3>
  Raw Material Cost: <input name="{{ p }}_raw" type="number"><br>
  Transport Cost: <input name="{{ p }}_trans" type="number"><br>
  Packing Cost: <input name="{{ p }}_pack" type="number"><br>
  Fumigation Cost: <input name="{{ p }}_fumi" type="number"><br>
  Customs Cost (Origin): <input name="{{ p }}_cust_o" type="number"><br>
  Export Duty (% of invoice): <input name="{{ p }}_duty" type="number"><br>
  Margin % (leave blank to use same): <input name="{{ p }}_margin" type="number"><br>
  Freight Cost: <input name="{{ p }}_freight" type="number"><br>
  Import Duty: <input name="{{ p }}_import_duty" type="number"><br>
  Customs (Destination): <input name="{{ p }}_cust_d" type="number"><br>
  Final Transport: <input name="{{ p }}_final_trans" type="number"><br>
  Distributor Margin %: <input name="{{ p }}_dist_margin" type="number"><br>
  Retailer Margin %: <input name="{{ p }}_ret_margin" type="number"><br>
  {% endfor %}
  <button type="submit">Save Estimate</button>
</form>
'''

template_view_estimates = style + '''
<h2>Saved Estimates</h2>
<ul>
  {% for e in estimates %}
    <li>{{ e['name'] }} - <a href="{{ url_for('view_estimate_detail', eid=e['id']) }}">View</a></li>
  {% endfor %}
</ul>
<a href="{{ url_for('dashboard') }}">Back</a>
'''

template_estimate_detail = style + '''
<h2>{{ estimate['name'] }}</h2>
<table>
  <tr><th>Product</th><th>Invoice Price</th><th>Importer Cost</th><th>Distributor Price</th><th>Retailer Price</th></tr>
  {% for p, d in estimate['products'].items() %}
  <tr><td>{{ p }}</td><td>{{ d['invoice_price'] }}</td><td>{{ d['importer_cost'] }}</td><td>{{ d['distributor_price'] }}</td><td>{{ d['retailer_price'] }}</td></tr>
  {% endfor %}
</table>
<a href="{{ url_for('view_estimates') }}">Back</a>
'''

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']
        if u in users and users[u]['password'] == p:
            session['username'] = u
            session['role'] = users[u]['role']
            return redirect(url_for('dashboard'))
    return render_template_string(template_login)

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template_string(template_dashboard)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/create', methods=['GET', 'POST'])
def create_estimate():
    if 'username' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        eid = str(uuid.uuid4())
        name = request.form['name']
        same_margin = float(request.form['same_margin'] or 0)
        estimate = {'id': eid, 'name': name, 'created': datetime.now(), 'products': {}}
        for p in products:
            raw = float(request.form.get(f'{p}_raw', 0))
            trans = float(request.form.get(f'{p}_trans', 0))
            pack = float(request.form.get(f'{p}_pack', 0))
            fumi = float(request.form.get(f'{p}_fumi', 0))
            cust_o = float(request.form.get(f'{p}_cust_o', 0))
            duty_perc = float(request.form.get(f'{p}_duty', 0))
            freight = float(request.form.get(f'{p}_freight', 0))
            import_duty = float(request.form.get(f'{p}_import_duty', 0))
            cust_d = float(request.form.get(f'{p}_cust_d', 0))
            final_trans = float(request.form.get(f'{p}_final_trans', 0))
            margin = request.form.get(f'{p}_margin')
            margin = float(margin) if margin else same_margin
            dist_margin = float(request.form.get(f'{p}_dist_margin', 0))
            ret_margin = float(request.form.get(f'{p}_ret_margin', 0))
            origin_cost = raw + trans + pack + fumi + cust_o
            invoice_price = origin_cost / (1 - margin/100)
            export_duty = invoice_price * duty_perc / 100
            importer_cost = origin_cost + export_duty + freight + import_duty + cust_d + final_trans
            distributor_price = importer_cost / (1 - dist_margin/100)
            retailer_price = distributor_price / (1 - ret_margin/100)
            estimate['products'][p] = {
                'invoice_price': round(invoice_price, 2),
                'importer_cost': round(importer_cost, 2),
                'distributor_price': round(distributor_price, 2),
                'retailer_price': round(retailer_price, 2)
            }
        estimates_db[eid] = estimate
        return redirect(url_for('view_estimates'))
    return render_template_string(template_create_estimate, products=products)

@app.route('/estimates')
def view_estimates():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template_string(template_view_estimates, estimates=list(estimates_db.values()))

@app.route('/estimate/<eid>')
def view_estimate_detail(eid):
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template_string(template_estimate_detail, estimate=estimates_db[eid])

if __name__ == '__main__':
    app.run(debug=True)
