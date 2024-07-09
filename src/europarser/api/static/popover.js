import 'https://unpkg.com/@popperjs/core@2/dist/umd/popper.js';

const tooltip_triggers = document.querySelectorAll(".tooltip-trigger");

tooltip_triggers.forEach((trigger) => {
        const parent = trigger.parentElement;
        const label = trigger.getAttribute('aria-label');
        const tooltip_ = document.querySelector("#" + label);

        const popperInstance = window.Popper.createPopper(trigger, tooltip_, {
            placement: 'right',
            modifiers: [
                {
                    name: 'offset',
                    options: {
                        offset: [0, 20],
                    },
                },
                {
                    name: 'flip',
                    options: {
                        fallbackPlacements: ['left', 'bottom'],
                    },
                },
                {
                    name: "boundary",

                }
            ],
        });
        const show = () => {
            // Make the tooltip visible
            tooltip_.setAttribute('data-show', '');

            // Enable the event listeners
            popperInstance.setOptions((options) => ({
                ...options,
                modifiers: [
                    ...options.modifiers,
                    {name: 'eventListeners', enabled: true},
                ],
            }));

            // Update its position
            popperInstance.update();
        }

        const hide = () => {
            // Hide the tooltip
            tooltip_.removeAttribute('data-show');

            // Disable the event listeners
            popperInstance.setOptions((options) => ({
                ...options,
                modifiers: [
                    ...options.modifiers,
                    {name: 'eventListeners', enabled: false},
                ],
            }));
        }

        const showEvents = ['mouseenter', 'focus'];
        const hideEvents = ['mouseleave', 'blur'];

        showEvents.forEach((event) => {
                parent.addEventListener(event, show);
            }
        );

        hideEvents.forEach((event) => {
                parent.addEventListener(event, hide);
            }
        );
    }
);
