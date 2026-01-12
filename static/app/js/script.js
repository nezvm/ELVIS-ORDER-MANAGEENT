function setCookie(name, value, days) {
    var expires = "";
    if (days) {
        var date = new Date();
        date.setTime(date.getTime() + days * 24 * 60 * 60 * 1000);
        expires = "; expires=" + date.toUTCString();
    }
    document.cookie = name + "=" + (value || "") + expires + "; path=/";
}

function getCookie(name) {
    var nameEQ = name + "=";
    var ca = document.cookie.split(";");
    for (var i = 0; i < ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0) == " ") c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
}

$(function () {
    "use strict";

    $("select.select:not(.offcanvas select,.home select)").select2({
        minimumResultsForSearch: "",
        placeholder: "Search",
        width: "100%",
        allowClear: true,
    });

    $('.offcanvas select').select2({
        minimumResultsForSearch: '',
        placeholder: "Search",
        width: '100%',
        allowClear: true,
        dropdownParent: $('.offcanvas')
    });

    $(".niceselect").select2({
        minimumResultsForSearch: -1,
        placeholder: "Search",
        width: "100%",
    });

    $(".selectmultiple").select2({
        minimumResultsForSearch: "",
        placeholder: "Search",
        width: "100%",
    });

    $(".select2").on("click", () => {
        let selectField = document.querySelectorAll(".select2-search__field");
        selectField.forEach((element, index) => {
            element?.focus();
        });
    });

    $("input.dateinput").bootstrapdatepicker({
        format: "dd/mm/yyyy",
        // format: "yyyy-mm-dd",
        viewMode: "date",
        multidate: false,
        multidateSeparator: "-",
        orientation: "bottom right",
        autoclose: true,
        todayHighlight: true,
    });

    // $('input.datetimeinput').bootstrapdatepicker({
    //     format: "dd/mm/yyyy hh:ii",
    //     viewMode: "time",
    //     multidate: false,
    //     multidateSeparator: "-",
    //     orientation: "bottom right"
    // })

    // $('input.timeinput').bootstrapdatepicker({
    //     format: "hh:ii",
    //     viewMode: "time",
    //     multidate: false,
    //     multidateSeparator: "-",
    //     orientation: "bottom right"
    // })

    $(".theme-layout").on("click", () => {
        if (document.body.className.split(" ").indexOf("dark-mode") >= 0) {
            setCookie("mode", "dark-mode", 7);
        }
        if (document.body.className.split(" ").indexOf("light-mode") >= 0) {
            setCookie("mode", "light-mode", 7);
        }
    });

    var mode = getCookie("mode");
    $("body").removeClass("light-mode");
    $("body").removeClass("dark-mode");
    $("body").addClass(mode);

    $(".timeinput").timepicker({
        timeFormat: "HH:mm",
        interval: 5,
        dynamic: true,
        dropdown: true,
        scrollbar: false,
    });

    $(document).on("click", ".instant-action-button", function (e) {
        e.preventDefault();
        var key = $(this).attr("data-key");
        var url = $(this).attr("data-url");
        var title = $(this).attr("data-title");
        $.ajax({
            type: "GET",
            url: url,
            dataType: "json",
            data: { pk: key },
            success: function (data) {
                var status = data.status;
                var message = data.message;
                if (status == "success") {
                    title ? (title = title) : (title = "Success");
                    $(`[data-key="${key}"]`).html(
                        `<i class="bi bi-check-square-fill text-success"></i>`
                    );
                    $(`span#${key}`).html(message);
                } else {
                    title ? (title = title) : (title = "An Error Occurred");
                    alert(message);
                }
            },
            error: function (data) {
                var title = "An error occurred";
                var message = "An error occurred. Please try again later.";
            },
        });
    });
    $(".form-horizontal-3").each(function () {
        $(this).addClass("row");
        $(this).find(".mb-3").addClass("col-lg-3 col-md-6 col-sm-4 col-12");
    });
    $(".form-horizontal-student_receipt").each(function () {
        $(this).addClass("row");
        $(this).find(".mb-3").addClass("col-lg-4 col-md-4 col-sm-6 col-12");
        $(this).find("#id_receipt_no").prop('readonly', true);

        // Check the payment method when the form is initially loaded
        var paymentMethod = $(this).find("#id_payment_method").val(); // Get the current value of the payment method select
        if (paymentMethod === "bank") {
            $(this).find("#id_bank").parent().removeClass("d-none");
        } else {
            $(this).find("#id_bank").parent().addClass("d-none");
        }

        // Also handle changes in payment method
        $(this).find("#id_payment_method").change(function () {
            var paymentMethod = $(this).val(); // Get the updated value
            if (paymentMethod === "bank") {
                $(".form-horizontal-student_receipt").find("#id_bank").parent().removeClass("d-none");
            } else {
                $(".form-horizontal-student_receipt").find("#id_bank").parent().addClass("d-none");
            }
        });
    });

    // add .row class to .form-horizontal and .col-md-3 to add its children with .mb-3 class
    $(".form-horizontal").each(function () {
        $(this).addClass("row");
        $(this).find(".mb-3").addClass("col-lg-4 col-md-4 col-sm-6 col-12");
    });
    $(".form-horizontal-6").each(function () {
        $(this).addClass("row");
        $(this).find(".mb-3").addClass("col-lg-6 col-md-6 col-sm-6 col-12");
    });
    // add .row class to .form-horizontal and .col-md-3 to add its children with .mb-3 class


    $("#reset-filter-search").click(function () {
        // Reset the form
        $("#global_search_bar").val('');
        // Submit the form after a short delay
        setTimeout(function () {
            $("#search-form").submit();
        }, 100);
    });

    $(document).on(
        "change",
        "#image_update_form input[type=file]",
        function () {
            var $this = $(this);
            var file = this.files[0];
            var reader = new FileReader();
            reader.onloadend = function () {
                $this
                    .closest(".avatar-xxl")
                    .css("background-image", "url(" + reader.result + ")");
            };
            if (file) {
                reader.readAsDataURL(file);
                $.ajax({
                    type: "POST",
                    url: "/employees/profile/",
                    data: new FormData($("#image_update_form")[0]),
                    processData: false,
                    contentType: false,
                    success: function (data) {
                        console.log(data);
                    },
                    error: function (data) {
                        console.log(data);
                    },
                });
            }
        }
    );
});

$(document).on("click", ".action-button", function (e) {
    e.preventDefault();
    $this = $(this);
    var html = $this.attr("data-text");
    var icon = "question";
    var id = $this.attr("data-id");
    
    var url = $this.attr("data-url");
    var title = $this.attr("data-title");
    if (!title) {
        title = "Are you sure?";
    }
    console.log('url', url);
    Swal.fire({
        title: title,
        html: html,
        icon: icon,
        showCancelButton: true,
    }).then((result) => {
        if (result.value) {
            window.setTimeout(function () {
                $.ajax({
                    type: "GET",
                    url: url,
                    dataType: "json",
                    data: { pk: id },

                    success: function (data) {
                        var message = data.message;
                        var status = data.status;
                        var reload = data.reload;
                        var redirect = data.redirect;
                        var redirect_url = data.redirect_url;
                        var title = data.title;

                        if (status == "true") {
                            title?title=title:title="Success";
                            Swal.fire({title:title,html:message,icon:"success"}).then(function(){"true"==redirect&&(window.location.href=redirect_url),"true"==reload&&window.location.reload()});
                        } else {
                            title?title=title:title="An Error Occurred";
                            Swal.fire({ title: title, html: message, icon: "error" });
                        }
                    },
                    error: function (data) {
                        var title = "An error occurred";
                        var message = "An error occurred. Please try again later.";
                        Swal.fire({ title: title, html: message, icon: "error" });
                    },
                });
            }, 100);
        } else {
            console.log("action cancelled");
        }
    });
});