function getNextDay(dateString) {
    var [day, month, year] = dateString.split('/').map(Number);
    var date = new Date(year, month - 1, day);
    date.setDate(date.getDate() + 1);
    var nextDayString = date.toLocaleDateString('en-GB');
    return nextDayString;
}


window.addEventListener("load", function () {
    (function ($) {
        $('#task_set-group .add-row > td > a').click(function () {
            console.log('new task added');
            var last_form = $('#task_set-group .form-row:not(.empty-form)').last().prev();
            var title = last_form.find('input[name$=title]').val();
            var description = last_form.find('textarea[name$=description]').val();
            var start_from = last_form.find('input[name$=start_from]').val(); // eg: 21/05/2023
            var end_before = last_form.find('input[name$=end_before]').val();
            var assigned_to = last_form.find('select[name$=assigned_to]').val();
            var status = last_form.find('select[name$=status]').val();
            console.log(title, description, start_from, end_before, assigned_to, status);

            // set the values of the new form
            var new_form = $('#task_set-group .form-row:not(.empty-form)').last();
            new_form.find('input[name$=title]').val(title);
            new_form.find('textarea[name$=description]').val(description);
            new_form.find('input[name$=start_from]').val(getNextDay(start_from));
            new_form.find('input[name$=end_before]').val(getNextDay(end_before));
            new_form.find('select[name$=assigned_to]').val(assigned_to);
            new_form.find('select[name$=status]').val(status);
        });
    })(django.jQuery);
});
