from django.urls import path
from . import views, dashboard_views

app_name = "donations"

urlpatterns = [
    path("",                  views.home,             name="home"),
    path("donate/",           views.donate,           name="donate"),
    path("donation/return/",  views.donation_return,  name="donation_return"),
    path("paynow/result/",    views.paynow_result,    name="paynow_result"),

    # ── Custom admin dashboard ────────────────────────────────────────────────
    path("dashboard/login/",     dashboard_views.dashboard_login,     name="dashboard_login"),
    path("dashboard/logout/",    dashboard_views.dashboard_logout,    name="dashboard_logout"),
    path("dashboard/",           dashboard_views.dashboard_index,     name="dashboard_index"),
    path("dashboard/donors/",    dashboard_views.dashboard_donors,    name="dashboard_donors"),
    path("dashboard/donations/", dashboard_views.dashboard_donations, name="dashboard_donations"),
]
