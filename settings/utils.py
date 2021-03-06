import ast
import os
import json
from http import HTTPStatus

from acl import lambda_handler as acl_handler
from db import lambda_handler as db_handler


def ok(data, invoke_from_http=True):
    return build_response(res=data, status_code=HTTPStatus.OK,
                          invoke_from_http=invoke_from_http)


def bad_request(errors=None, invoke_from_http=True):
    message = {'message': 'Bad request'} if not errors else errors
    return build_response(err=message,
                          status_code=HTTPStatus.BAD_REQUEST,
                          invoke_from_http=invoke_from_http)


def build_response(err=None, res=None, status_code=HTTPStatus.OK, invoke_from_http=True):
    if invoke_from_http:
        response = {
            'statusCode': status_code,
            'body': json.dumps(err) if err else json.dumps(res),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
    else:
        response = {
            'statusCode': status_code,
            'body': err if err else res
        }

    return response


def internal_server_error(invoke_from_http=True):
    return build_response(
        err={'message': 'Internal server error.'},
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        invoke_from_http=invoke_from_http
    )


def forbidden(err=None, invoke_from_http=True):
    if not err:
        err = {'message': 'User does not have privileges to perform this action'}
    return build_response(
        err=err,
        status_code=HTTPStatus.FORBIDDEN,
        invoke_from_http=invoke_from_http
    )


def get_cognito_email(event):
    request_context = event.get('requestContext', {})
    authorizer = request_context.get('authorizer', {})

    open_id_sub = None
    if authorizer:
        claims = authorizer['claims']
        if claims:
            open_id_sub = claims['email']
    return open_id_sub


def get_enviroment_var(key, default=None):
    return os.environ[key] if key in os.environ.keys() else default


def get_body_or_bad_request(event):
    response = {'error': False, 'response': None}

    body = event.get('body')
    if not body:
        error = {'message': 'The BODY is empty.'}

        response['error'] = True
        response['response'] = bad_request(error)
        return response
    try:
        response['error'] = False
        response['response'] = json.loads(body)
        return response
    except ValueError:
        error = {'message': 'Malformed JSON in request body.'}

        response['error'] = True
        response['response'] = bad_request(error)
        return response


def get_user_id_by_email(email):
    sql = f'''
        select u.id
        from users.users as u
        where u.email = '{email}'
    '''

    msg = {
        'body': {
            'action': 'run',
            'queries': [sql]
        }
    }

    print(msg)

    method, response = db_handler(msg)
    print(type(response))
    print(response)

    if method == 'ok':
        body = ast.literal_eval(response[0])
        print(body)
        return body[0]['id']

    return None


def get_current_user_permission(user_id, permission):
    msg = {
        'body': {
            'action': 'check-user-permissions',
            'user_id': user_id,
            'permission': permission
        }
    }

    method, response = acl_handler(msg)

    print(response)

    if method == 'ok':
        return response

    return None
