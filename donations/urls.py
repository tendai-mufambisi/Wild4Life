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

    # ── Dashboard — site settings ─────────────────────────────────────────────
    path("dashboard/settings/", dashboard_views.site_settings_edit, name="site_settings"),

    # ── Dashboard — team ──────────────────────────────────────────────────────
    path("dashboard/team/",                         dashboard_views.team_list,   name="team_list"),
    path("dashboard/team/new/",                     dashboard_views.team_create, name="team_create"),
    path("dashboard/team/<int:member_id>/edit/",    dashboard_views.team_edit,   name="team_edit"),
    path("dashboard/team/<int:member_id>/delete/",  dashboard_views.team_delete, name="team_delete"),

    # ── Dashboard — testimonials ──────────────────────────────────────────────
    path("dashboard/testimonials/",                       dashboard_views.testimonial_list,   name="testimonial_list"),
    path("dashboard/testimonials/new/",                   dashboard_views.testimonial_create, name="testimonial_create"),
    path("dashboard/testimonials/<int:item_id>/edit/",    dashboard_views.testimonial_edit,   name="testimonial_edit"),
    path("dashboard/testimonials/<int:item_id>/delete/",  dashboard_views.testimonial_delete, name="testimonial_delete"),

    # ── Dashboard — gallery ───────────────────────────────────────────────────
    path("dashboard/gallery/",                       dashboard_views.gallery_manage, name="gallery_manage"),
    path("dashboard/gallery/<int:image_id>/delete/", dashboard_views.gallery_delete, name="gallery_delete"),

    # ── Dashboard — FAQs ──────────────────────────────────────────────────────
    path("dashboard/faqs/",                    dashboard_views.faq_list,   name="faq_list"),
    path("dashboard/faqs/new/",                dashboard_views.faq_create, name="faq_create"),
    path("dashboard/faqs/<int:faq_id>/edit/",  dashboard_views.faq_edit,   name="faq_edit"),
    path("dashboard/faqs/<int:faq_id>/delete/",dashboard_views.faq_delete, name="faq_delete"),
]
