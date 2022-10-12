import os
import functools
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, flash, request, redirect, url_for, jsonify,session,make_response,send_file,g
import utils as utils
from db import close_db, get_db
from formulario import Contactenos,Enviar
from message import mensajes

app = Flask( __name__ )
app.secret_key = os.urandom( 24 )


@app.route( '/' )
def index():
    if g.user:
        return redirect(url_for ('send'))
    return render_template( 'login.html' )


@app.route( '/register', methods=('GET', 'POST') )
def register():
    if g.user:
        return redirect(url_for ('send'))
    try:
        if request.method == 'POST':
            
            name= request.form['nombre']
            username = request.form['username']
            password = request.form['password']
            password_hash = generate_password_hash(password)
            email = request.form['correo']
            error = None
            db = get_db()

            if not utils.isUsernameValid( username ):
                error = "El usuario debe ser alfanumerico o incluir solo '.','_','-'"
                flash( error )
                return render_template( 'register.html' )

            if not utils.isPasswordValid( password ):
                error = 'La contraseña debe contenir al menos una minúscula, una mayúscula, un número, un caracter especial y 8 caracteres'
                flash( error )
                return render_template( 'register.html' )

            if not utils.isEmailValid( email ):
                error = 'Correo invalido'
                flash( error )
                return render_template( 'register.html' )

            if db.execute( 'SELECT * FROM usuario WHERE correo = ?', (email,) ).fetchone() is not None:
                error = 'El correo ya existe'.format( email )
                flash( error )
                return render_template( 'register.html' )
           
            db.executescript(
                "INSERT INTO usuario (nombre, usuario, correo, contraseña) VALUES ('%s','%s','%s','%s')" % (name, username, email, password_hash)
            )
            db.commit()

            close_db()

            flash( 'Revisa tu correo para activar tu cuenta' )
            return redirect( 'login' )
        return render_template( 'register.html' )
    except:
        return render_template( 'register.html' )


@app.route( '/login', methods=('GET', 'POST') )
def login():
    try:
        if request.method == 'POST':
            db = get_db()
            error = None
            username = request.form['username']
            password = request.form['password']

            if not username:
                error = 'Debes ingresar el usuario'
                flash( error )
                return render_template( 'login.html' )

            if not password:
                error = 'Contraseña requerida'
                flash( error )
                return render_template( 'login.html' )
            
            user = db.execute(
                'SELECT * FROM usuario WHERE usuario = ? ', (username,)
            ).fetchone()

            close_db()

            if user is None:
                error = 'Usuario o contraseña inválidos'
            else:
                save_password = user[4]
                resultado = check_password_hash(save_password,password)
                if resultado is False:
                    flash('Usuario o contraseña Invalidos') 
                else:
                    session.clear() 
                    session['user_id'] = user[0]
                    resp = make_response( redirect( url_for( 'send' ) ) )
                    resp.set_cookie( 'username', username )
                    return resp
                return render_template( 'login.html' )
            flash( error )
        return render_template( 'login.html' )
    except:
        return render_template( 'login.html' )

def login_required(view):
    @functools.wraps( view )
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect( url_for( 'login' ) )
        return view( **kwargs )
    return wrapped_view

@app.route( '/logout')
@login_required
def logout():
    session.clear()
    return redirect( url_for( 'login' ) ) 

@app.route( '/contacto', methods=('GET', 'POST') )
def contacto():
    form = Contactenos()
    return render_template( 'contacto.html', titulo='Contactenos', form=form )


@app.route( '/message', methods=('GET', 'POST') )
def message():
    print( "Retrieving info" )
    return jsonify( {'mensajes': mensajes} )

@app.route('/send',methods =('GET','POST'))
@login_required
def send():
    form = Enviar()
    if request.method =='POST':
        de = g.user[0]
        para = request.form['para']
        asunto = request.form['asunto']
        mensaje = request.form['mensaje']
        name = request.cookies.get('username')

        if not para:
            error = ' Debes ingresar el usuario al que se enviara el mensaje'
            flash( name + error )
            return render_template( 'send.html' , titulo='Enviar', form=form)
 
        if not asunto:
            error = ' Porfavor escriba un asunto del mensaje'
            flash( name + error )
            return render_template( 'send.html' , titulo='Enviar', form=form)
 
        if not mensaje:
            error = ' Escriba un mensaje para ser enviado'
            flash( name + error )
            return render_template( 'send.html' , titulo='Enviar', form=form)
        db = get_db()
        
        para =  db.execute('SELECT * FROM usuario WHERE  usuario = ?',(para,)
        ).fetchone()
        if para is None:
            flash('No existe el usuario')
        else:
            db.execute('INSERT INTO mensajes (from_id, to_id, asunto, mensaje) VALUES(?,?,?,?)',(de,para[0],asunto,mensaje))
            db.commit()
            flash("Mensaje enviado con exito")
        close_db()
 
    return render_template ('send.html' , titulo='Enviar', form=form)

@app.route( '/downloadpdf')
@login_required
def downloadpdf():
    return send_file( "resources/doc.pdf", as_attachment=True)
 
@app.route( '/downloadimage', methods=('GET', 'POST') )
@login_required
def downloadimage():
    return send_file( "resources/image.png", as_attachment=True )

@app.before_request
def load_logged_in_user():
    user_id = session.get( 'user_id' )
    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM usuario WHERE id = ?', (user_id,)
        ).fetchone()
        close_db()

if __name__ == '__main__':
    app.run()
