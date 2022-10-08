import functools
import os
from re import X

from flask import Flask, render_template, flash, request, redirect, url_for, session, send_file, current_app, g, make_response

import utils
from db import get_db, close_db
from werkzeug.security import generate_password_hash, check_password_hash
from formulario import Contactenos
from message import mensajes

app = Flask( __name__ )
app.secret_key = os.urandom( 24 )


@app.route( '/' )
def index():
    if g.user:
        return redirect( url_for( 'send' ) )
    return render_template( 'login.html' )


@app.route( '/register', methods=('GET', 'POST') )
def register():
    if g.user:
        return redirect( url_for( 'send' ) )
    try:
        if request.method == 'POST':
            name= request.form['nombre']
            username = request.form['username']
            password = request.form['password']
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

            db.execute(
                'INSERT INTO usuario (nombre, usuario, correo, contraseña) VALUES (?,?,?,?)',
                (name, username, email, generate_password_hash(password))
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
        if g.user:
            return redirect( url_for( 'send' ) )
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
                'SELECT * FROM usuario WHERE usuario = ? AND contraseña = ?', (username, password)
            ).fetchone()

            if user is None:
                user = db.execute(
                    'SELECT * FROM usuario WHERE usuario = ?', (username,)
                ).fetchone()
                if user is None:
                    error = 'Usuario no existe'
                else:
                    #Validar contraseña hash            
                    store_password = user[4]
                    result = check_password_hash(store_password, password)
                    if result is False:
                        error = 'Contraseña inválida'
                    else:
                        session.clear()
                        session['user_id'] = user[0]
                        resp = make_response( redirect( url_for( 'send' ) ) )
                        resp.set_cookie( 'username', username )
                        return resp
                    flash( error )
            else:
                session.clear()
                session['user_id'] = user[0]
                return redirect( url_for( 'send' ) )
            flash( error )
            close_db()
        return render_template( 'login.html' )
    except Exception as e:
        print(e)
        return render_template( 'login.html' )


@app.route( '/contacto', methods=('GET', 'POST') )
def contacto():
    form = Contactenos()
    return render_template( 'contacto.html', titulo='Contactenos', form=form )


def login_required(view):
    @functools.wraps( view )
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect( url_for( 'login' ) )

        return view( **kwargs )

    return wrapped_view


@app.route( '/downloadpdf', methods=('GET', 'POST') )
# @login_required
def downloadpdf():
    return send_file( "resources/doc.pdf", as_attachment=True )


@app.route( '/downloadimage', methods=('GET', 'POST') )
@login_required
def downloadimage():
    return send_file( "resources/image.png", as_attachment=True )


@app.route( '/send', methods=('GET', 'POST') )
@login_required
def send():
    if request.method == 'POST':
        from_id = g.user['id']
        to_username = request.form['para']
        subject = request.form['asunto']
        body = request.form['mensaje']
        db = get_db()

        if not to_username:
            flash( 'Para campo requerido' )
            return render_template( 'send.html' )

        if not subject:
            flash( 'Asunto es requerido' )
            return render_template( 'send.html' )

        if not body:
            flash( 'Mensaje es requerido' )
            return render_template( 'send.html' )

        error = None
        userto = None

        userto = db.execute(
            'SELECT * FROM usuario WHERE usuario = ?', (to_username,)
        ).fetchone()

        if userto is None:
            error = 'No existe ese usuario'

        if error is not None:
            flash( error )
        else:
            db = get_db()
            db.execute(
                'INSERT INTO mensajes (from_id, to_id, asunto, mensaje)'
                ' VALUES (?, ?, ?, ?)',
                (g.user['id'], userto['id'], subject, body)
            )
            db.commit()
            
            flash( "Mensaje Enviado" )
        
        close_db()
    return render_template( 'send.html' )

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


@app.route( '/logout' )
def logout():
    session.clear()
    return redirect( url_for( 'login' ) )


if __name__ == '__main__':
    app.run()