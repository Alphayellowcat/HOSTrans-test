list_widget_style = """
            QListWidget {
                background-color: rgba(100, 100, 200, 0.2);
                color: white;
                border: 1px solid rgba(100, 100, 200, 0.3);
                border-radius: 5px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid rgba(100, 100, 200, 0.1);
            }
            QListWidget::item:hover {
                background-color: rgba(100, 100, 200, 0.3);
            }
        """

main_style = """
            QWidget {
                background-color: rgba(100, 100, 255, 0.3);
            }
        """

title_label_style = "color: white; font-size: 16px;"