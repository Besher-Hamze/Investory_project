from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard, name='dashboard'),

    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_create, name='product_create'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('products/<int:pk>/barcode/', views.product_barcode, name='product_barcode'),

    path('warehouses/', views.warehouse_list, name='warehouse_list'),
    path('warehouses/add/', views.warehouse_create, name='warehouse_create'),
    path('warehouses/<int:pk>/edit/', views.warehouse_edit, name='warehouse_edit'),
    path('warehouses/<int:pk>/', views.warehouse_detail, name='warehouse_detail'),

    path('operations/in/', views.stock_in_view, name='stock_in'),
    path('operations/out/', views.stock_out_view, name='stock_out'),
    path('operations/transfer/', views.transfer_view, name='transfer'),
    path('operations/scanner/', views.barcode_scanner, name='barcode_scanner'),
    path('api/generate-barcode/', views.api_generate_barcode, name='api_generate_barcode'),
    path('api/product-by-barcode/', views.api_product_by_barcode, name='api_product_by_barcode'),

    path('movements/', views.movement_log, name='movement_log'),

    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/<int:pk>/read/', views.notification_mark_read, name='notification_mark_read'),
    path('notifications/read-all/', views.notifications_mark_all_read, name='notifications_mark_all_read'),

    path('reports/current-stock/', views.report_current_stock, name='report_current_stock'),
    path('reports/turnover/', views.report_turnover, name='report_turnover'),
    path('reports/slow-moving/', views.report_slow_moving, name='report_slow_moving'),
    path('reports/financial/', views.report_financial, name='report_financial'),
    path('reports/pdf/<str:report_type>/', views.report_pdf, name='report_pdf'),
]
