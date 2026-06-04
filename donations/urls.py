from django.urls import path
from . import views, dashboard_views

app_name = "donations"

urlpatterns = [
    # ── Public site ─────────────────────────────────────────────────────────
    path("",                views.home,          name="home"),
    path("about/",          views.about,         name="about"),
    path("services/",       views.services,      name="services"),
    path("gallery/",        views.gallery,       name="gallery"),
    path("team/",           views.team,          name="team"),
    path("testimonials/",   views.testimonials,  name="testimonials"),
    path("contact/",        views.contact,       name="contact"),
    path("contact/submit/", views.contact_submit, name="contact_submit"),

    # ── Blog (public) ────────────────────────────────────────────────────────
    path("blog/",           views.blog_list,     name="blog_list"),
    path("blog/<slug:slug>/", views.blog_detail, name="blog_detail"),

    # ── Donation flow ────────────────────────────────────────────────────────
    path("donate/",           views.donate,           name="donate"),
    path("donation/return/",  views.donation_return,  name="donation_return"),
    path("paynow/result/",    views.paynow_result,    name="paynow_result"),

    # ── Dashboard — auth ─────────────────────────────────────────────────────
    path("dashboard/login/",  dashboard_views.dashboard_login,  name="dashboard_login"),
    path("dashboard/logout/", dashboard_views.dashboard_logout, name="dashboard_logout"),

    # ── Dashboard — analytics ────────────────────────────────────────────────
    path("dashboard/",           dashboard_views.dashboard_index,     name="dashboard_index"),
    path("dashboard/donors/",    dashboard_views.dashboard_donors,    name="dashboard_donors"),
    path("dashboard/donations/", dashboard_views.dashboard_donations, name="dashboard_donations"),

    # ── Dashboard — blog ─────────────────────────────────────────────────────
    path("dashboard/blog/",              dashboard_views.blog_list,   name="blog_list_dash"),
    path("dashboard/blog/new/",          dashboard_views.blog_create, name="blog_create"),
    path("dashboard/blog/<uuid:post_id>/edit/",   dashboard_views.blog_edit,   name="blog_edit"),
    path("dashboard/blog/<uuid:post_id>/delete/", dashboard_views.blog_delete, name="blog_delete"),

    # ── Dashboard — users ────────────────────────────────────────────────────
    path("dashboard/users/",             dashboard_views.user_list,   name="user_list"),
    path("dashboard/users/new/",         dashboard_views.user_create, name="user_create"),
    path("dashboard/users/<int:user_id>/edit/",   dashboard_views.user_edit,   name="user_edit"),
    path("dashboard/users/<int:user_id>/delete/", dashboard_views.user_delete,  name="user_delete"),
    path("dashboard/password/",                   dashboard_views.change_password, name="change_password"),
]
