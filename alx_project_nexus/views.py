# project level views
from rest_framework import urls
from rest_framework.response import Response
def index(request):
    # TODO check session active
    # TODO check which user for specific app(auth will handle such for API external request)
    
    # login/register
    if not request.user.is_authenticated:
        # show login form
        # return Response(urls.rest_framework.api-auth)
        pass
    