echo "Запуск нагрузочного тестирования..."
echo "Ожидаемый RPS: 5"
echo "SLI времени ответа: 300 мс"
echo "SLI успешности: 99.9%"
echo ""

locust -f ../locustfile.py \
    --headless \
    --users 5 \
    --spawn-rate 1 \
    --run-time 60s \
    --host http://localhost:8080 \
    --html load_test_report.html \
    --csv load_test_results

echo ""
echo "Тестирование завершено. Результаты сохранены в:"
echo "- load_test_report.html"
echo "- load_test_results.csv"

